"""
Booking Agent — CarePlus Clinic
================================
Main LangGraph conversation graph for appointment booking.
The emergency sub-agent lives in agents/emergency_agent.py and is
mounted here as the `emergency_handler` node.
"""

from __future__ import annotations

import functools
from typing import Any, Dict, List, Optional, TypedDict
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from groq import Groq

from tools.doctor_service import (
    get_specialist_list,
    get_doctors_by_speciality,
    find_doctor_by_id,
    find_customer_by_phone,
    get_doctors_info,
    generate_time_slot,
)
from data.db import get_customer_by_phone, get_bookings_by_patient_id, get_doctor_by_id
from tools.booking_service import (
    get_or_create_customer,
    get_available_slots,
    confirm_booking,
    get_booking_details,
)
from tools.email_service import generate_ics_file, send_confirmation_email
from agent.emergency_agent import emergency_handler_node
from agent.reschedule_agent import reschedule_handler_node

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


from agent.state import BookingState, create_initial_stand


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 20,
    temperature: float = 0,
) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        print(f"[LLM] {content!r}")
        return content
    except Exception as exc:
        print(f"[LLM] Error: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Guardrail classifier
# ---------------------------------------------------------------------------

def classify_message(conversation_snippet: str, current_stage: str) -> str:
    """
    Returns: "yes" | "no" | "emergency"
    yes       -> on-topic for booking
    no        -> off-topic, redirect
    emergency -> life-threatening situation
    """
    stage_context = {
        "greeting":          "initial greeting",
        "select_speciality": "choosing a medical speciality",
        "select_doctor":     "choosing a doctor",
        "select_date":       "selecting a date",
        "select_slot":       "selecting a time slot",
        "collect_details":   "collecting patient details",
        "confirm":           "confirming the appointment",
        "emergency_handler": "handling a medical emergency",
    }
    context = stage_context.get(current_stage, "general booking")

    result = call_llm(
        system_prompt=(
            "You are an intent classifier for a medical clinic booking chatbot.\n"
            "Respond with ONLY one word:\n"
            "- 'yes' if the message is about booking an appointment, choosing options, "
            "selecting dates/times, confirming, or any step in the booking process\n"
            "- 'reschedule' ONLY if the user explicitly says they want to cancel, change, "
            "modify, or reschedule an EXISTING/PREVIOUS appointment (NOT the current one being booked)\n"
            "- 'emergency' if the user describes a life-threatening situation "
            "(severe chest pain, stroke, heavy bleeding, heart attack, difficulty breathing, etc.)\n"
            "- 'no' for anything else (small talk, unrelated questions)\n"
            "IMPORTANT: During an active booking flow (selecting speciality, doctor, date, time, "
            "or confirming), always classify as 'yes' unless clearly emergency or off-topic.\n"
            "One word only. No punctuation."
        ),
        user_prompt=(
            f"Stage context: {context}\n"
            f"Conversation:\n{conversation_snippet}\n\n"
            "Classify:"
        ),
        max_tokens=5,
        temperature=0,
    )
    return result.strip().lower()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

VALID_ROUTES_PER_STAGE: Dict[str, set] = {
    "greeting":          {"greeting", "select_speciality", "cancelled", "emergency_handler", "reschedule_handler"},
    "select_speciality": {"select_speciality", "select_doctor", "emergency_handler", "reschedule_handler"},
    "select_doctor":     {"select_doctor", "select_date", "emergency_handler", "reschedule_handler"},
    "select_date":       {"select_date", "select_slot", "emergency_handler", "reschedule_handler"},
    "select_slot":       {"select_slot", "confirm", "emergency_handler", "reschedule_handler"},
    "confirm":           {"confirm", "collect_details", "cancelled", "select_slot", "emergency_handler", "reschedule_handler"},
    "collect_details":   {"collect_details", "completed", "emergency_handler", "reschedule_handler"},
    "emergency_handler": {"emergency_handler", "greeting", "cancelled"},
    "reschedule_handler": {"reschedule_handler", "greeting", "cancelled"},
}

ROUTING_PROMPTS: Dict[str, str] = {
    "greeting": (
        "Does the user want to book an appointment?\n"
        "Reply with ONLY one of: greeting | select_speciality | cancelled"
    ),
    "select_speciality": (
        "Has the user chosen a medical speciality?\n"
        "Reply with ONLY one of: select_speciality | select_doctor | cancelled"
    ),
    "select_date": (
        "Has the user chosen a date?\n"
        "Reply with ONLY one of: select_date | select_slot | cancelled"
    ),
    "select_slot": (
        "Has the user chosen a time slot?\n"
        "Reply with ONLY one of: select_slot | confirm | cancelled"
    ),
    "confirm": (
        "Did the user confirm the appointment details?\n"
        "Reply with EXACTLY ONE of the following:\n"
        "- collect_details (if they confirmed or said yes)\n"
        "- select_slot (if they want to change the time)\n"
        "- cancelled (if they want to cancel)\n"
        "- confirm (if they haven't answered yet)"
    ),
    "emergency_handler": (
        "Has the user asked to cancel emergency mode or return to booking?\n"
        "Reply with ONLY one of: emergency_handler | greeting | cancelled"
    ),
    "reschedule_handler": (
        "Has the user asked to return to the main menu?\n"
        "Reply with ONLY one of: reschedule_handler | greeting | cancelled"
    ),
}


def llm_router(state: BookingState, k: int = 4) -> str:
    current_stage = state.get("stage", "greeting")
    messages      = state.get("messages", [])
    snippet       = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages[-k:]
    )

    # Fast-path state bypasses
    if current_stage == "select_speciality" and state.get("selected_speciality"):
        return "select_doctor"
    if current_stage == "select_date" and state.get("selected_date"):
        return "select_slot"
    if current_stage == "select_slot" and state.get("selected_time"):
        return "confirm"
        
    last_msg = messages[-1]["content"].lower() if messages else ""
    if "manage appointment" in last_msg or "cancel appointment" in last_msg:
        return "reschedule_handler"
    if current_stage == "confirm" and last_msg == "confirm":
        return "collect_details"

    # Guardrail
    if messages:
        verdict = classify_message(snippet, current_stage)

        if verdict == "emergency":
            print("[Router] Emergency → emergency_handler")
            return "emergency_handler"
        
        # Only allow reschedule redirect from greeting stage or if user explicitly asked
        if verdict == "reschedule" and current_stage in ("greeting",):
            print("[Router] Reschedule → reschedule_handler")
            return "reschedule_handler"

        if verdict == "no":
            print("[Router] Off-topic → staying, redirecting")
            try:
                redirect = call_llm(
                    system_prompt=(
                        "You are a friendly clinic assistant. "
                        "The user went off-topic. Politely redirect in 1-2 sentences."
                    ),
                    user_prompt=f"Conversation:\n{snippet}\nGenerate a polite redirect:",
                    max_tokens=60,
                    temperature=0.3,
                )
            except Exception:
                redirect = "I'm here to help with appointment booking. Shall we continue?"
            state["messages"].append({"role": "assistant", "content": redirect})
            return current_stage

    # Stage routing
    if current_stage not in ROUTING_PROMPTS:
        return current_stage

    try:
        raw = call_llm(
            system_prompt=(
                "You are a routing classifier for a booking chatbot. "
                "Reply with ONLY the exact route name."
            ),
            user_prompt=f"Conversation:\n{snippet}\n\n{ROUTING_PROMPTS[current_stage]}",
            max_tokens=20,
            temperature=0,
        )
        route = raw.strip().strip("\"'").lower()
    except Exception as exc:
        print(f"[Router] Error: {exc}")
        return current_stage

    valid = VALID_ROUTES_PER_STAGE.get(current_stage, {current_stage})
    if route not in valid:
        print(f"[Router] Invalid route '{route}' for '{current_stage}' → staying")
        return current_stage

    print(f"[Router] {current_stage} → {route}")
    return route


# ---------------------------------------------------------------------------
# Booking nodes
# ---------------------------------------------------------------------------

def greeting_node(state: BookingState) -> BookingState:
    state["stage"] = "greeting"
    last_role = state["messages"][-1]["role"] if state["messages"] else None

    if last_role != "assistant":
        try:
            msg = call_llm(
                system_prompt=(
                    "You are a friendly clinic booking assistant. "
                    "Greet the user warmly and ask if they'd like to book an appointment. "
                    "One sentence only."
                ),
                user_prompt="Generate a welcome greeting.",
                max_tokens=60,
                temperature=0.3,
            ) or "Welcome to CarePlus Clinic! Would you like to book an appointment?"
        except Exception:
            msg = "Welcome to CarePlus Clinic! Would you like to book an appointment?"

        state["messages"].append({
            "role": "assistant",
            "content": msg,
            "options": ["Book Appointment", "Manage Appointments"]
        })

    user_input = interrupt({
        "content": state["messages"][-1]["content"],
        "options": ["Book Appointment", "Manage Appointments"]
    })
    state["messages"].append({"role": "user", "content": user_input})
    return state


def select_speciality_node(state: BookingState) -> BookingState:
    state["stage"] = "select_speciality"
    specialities  = get_specialist_list()
    options_str   = "\n".join(f"- {s}" for s in specialities)
    msg = f"Please choose a medical speciality:\n{options_str}"

    if not state["messages"] or state["messages"][-1].get("content") != msg:
        state["messages"].append({"role": "assistant", "content": msg, "options": specialities})

    raw = interrupt({"content": msg, "options": specialities})
    state["messages"].append({"role": "user", "content": raw})

    extracted = call_llm(
        system_prompt="Extract information. Return ONLY the exact match or UNKNOWN.",
        user_prompt=(
            f'Extract the medical speciality from: "{raw}"\n'
            f'Available: {", ".join(specialities)}\n'
            "Return ONLY the exact name or UNKNOWN."
        ),
        max_tokens=30,
    ).strip()

    selected = next(
        (s for s in specialities
         if s.lower() in extracted.lower() or extracted.lower() in s.lower()),
        None
    )
    if selected:
        state["selected_speciality"] = selected
        state["available_options"]   = specialities
    else:
        state["messages"].append({
            "role": "assistant",
            "content": f"I didn't recognise that. Please pick from: {', '.join(specialities)}"
        })
    return state


def select_doctor_node(state: BookingState) -> BookingState:
    speciality = state["selected_speciality"]
    doctor     = get_doctors_info(speciality)

    if not doctor:
        state["messages"].append({
            "role": "assistant",
            "content": "Sorry, no doctor available for that speciality. Please select a different one.",
        })
        state["stage"] = "select_speciality"
        return state

    state["selected_doctor"] = doctor
    state["stage"]            = "select_date"
    state["messages"].append({
        "role": "assistant",
        "content": f"Great! You'll be seeing **{doctor.get('name', 'our doctor')}** ({speciality}). Let's pick a date."
    })
    return state


def select_date_node(state: BookingState) -> BookingState:
    state["stage"] = "select_date"
    today     = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    tmrw_str  = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    options   = ["Today", "Tomorrow", "Next Monday"]

    doc_name = (
        state["selected_doctor"].get("name", "the doctor")
        if state["selected_doctor"] else "the doctor"
    )
    msg = (
        f"When would you like to visit {doc_name}? "
        "Pick an option or type a date like 'Next Friday' or 'May 15th'."
    )

    if not state["messages"] or state["messages"][-1].get("content") != msg:
        state["messages"].append({"role": "assistant", "content": msg, "options": options})

    raw = interrupt({"content": msg, "options": options})
    state["messages"].append({"role": "user", "content": raw})

    extracted = call_llm(
        system_prompt="Extract and calculate dates. Return ONLY YYYY-MM-DD or UNKNOWN.",
        user_prompt=(
            f'User said: "{raw}"\n'
            f"Today is {today.strftime('%Y-%m-%d (%A)')}.\n"
            f"Today={today_str}, Tomorrow={tmrw_str}.\n"
            "Return ONLY the date in YYYY-MM-DD format or UNKNOWN."
        ),
        max_tokens=15,
    ).strip()

    if extracted != "UNKNOWN" and "-" in extracted:
        state["selected_date"] = extracted
    else:
        state["messages"].append({
            "role": "assistant",
            "content": "I couldn't parse that date. Please say 'Today', 'Tomorrow', or a specific date."
        })
    return state


def select_slot_node(state: BookingState) -> BookingState:
    state["stage"] = "select_slot"
    doctor = state["selected_doctor"]
    date   = state["selected_date"]
    slots  = generate_time_slot(doctor["office_hours"])
    msg    = f"Available time slots for {doctor['name']} on {date}:"

    if not state["messages"] or state["messages"][-1].get("content") != msg:
        state["messages"].append({"role": "assistant", "content": msg, "options": slots})

    raw = interrupt({"content": msg, "options": slots})
    state["messages"].append({"role": "user", "content": raw})

    extracted = call_llm(
        system_prompt="Extract time slots. Return ONLY the exact match or UNKNOWN.",
        user_prompt=(
            f'Extract the time slot from: "{raw}"\n'
            f"Available: {', '.join(slots)}\n"
            "Return ONLY the exact slot or UNKNOWN."
        ),
        max_tokens=15,
    ).strip()

    selected = next((s for s in slots if s.lower() in extracted.lower()), None)
    if selected:
        state["selected_time"] = selected
    else:
        state["messages"].append({
            "role": "assistant",
            "content": f"I didn't recognise that. Please pick from: {', '.join(slots)}"
        })
    return state


def confirm_node(state: BookingState) -> BookingState:
    state["stage"] = "confirm"
    doctor  = state["selected_doctor"]
    options = ["Confirm", "Cancel", "Change Slot"]
    msg = (
        f"Please review your appointment:\n\n"
        f"**Doctor:** {doctor.get('name', '—')}\n"
        f"**Speciality:** {doctor.get('speciality', '—')}\n"
        f"**Date:** {state.get('selected_date', 'Today')}\n"
        f"**Time:** {state.get('selected_time', '—')}\n\n"
        f"Shall I confirm this booking?"
    )

    if not state["messages"] or state["messages"][-1].get("content") != msg:
        state["messages"].append({"role": "assistant", "content": msg, "options": options})

    user_choice = interrupt({"content": msg, "options": options})
    state["messages"].append({"role": "user", "content": user_choice})
    return state


def collect_details_node(state: BookingState) -> BookingState:
    """One interrupt per execution — loops back via conditional edge."""
    state["stage"] = "collect_details"

    if not state.get("customer_name"):
        msg = "Please enter your full name."
        if not state["messages"] or state["messages"][-1].get("content") != msg:
            state["messages"].append({"role": "assistant", "content": msg, "options": []})
        name = interrupt({"content": msg, "options": []})
        state["messages"].append({"role": "user", "content": name})
        state["customer_name"] = name
        return state

    if not state.get("customer_phone"):
        msg = "Please enter your phone number:"
        if not state["messages"] or state["messages"][-1].get("content") != msg:
            state["messages"].append({"role": "assistant", "content": msg, "options": []})
        phone = interrupt({"content": msg, "options": []})
        state["messages"].append({"role": "user", "content": phone})
        state["customer_phone"] = phone
        return state

    if not state.get("customer_email"):
        msg = "Finally, please enter your email address for the calendar invite:"
        if not state["messages"] or state["messages"][-1].get("content") != msg:
            state["messages"].append({"role": "assistant", "content": msg, "options": []})
        email = interrupt({"content": msg, "options": []})
        state["messages"].append({"role": "user", "content": email})
        state["customer_email"] = email

    return state


def completed_node(state: BookingState) -> BookingState:
    state["stage"] = "completed"
    doctor = state["selected_doctor"]

    booking_id = confirm_booking(
        doctor_id=doctor.get("doctor_id") or doctor.get("doctors_id"),
        patient_name=state["customer_name"],
        patient_phone=state["customer_phone"],
        date=state["selected_date"],
        time=state["selected_time"],
        patient_email=state.get("customer_email")
    )
    state["booking_id"] = booking_id
    
    # Generate ICS string
    try:
        ics_data = generate_ics_file(
            state["customer_name"], 
            doctor.get('name', 'Doctor'), 
            state["selected_date"], 
            state["selected_time"]
        )
        state["ics_data"] = ics_data
    except Exception as e:
        print(f"Error generating ICS: {e}")
        state["ics_data"] = None

    # Send confirmation emails
    doctor_email = doctor.get("email") or f"{doctor.get('name', 'doctor').lower().replace(' ', '.').replace('dr.', 'dr')}@CarePlus.com"
    send_confirmation_email(
        to_email=state.get("customer_email", "patient@example.com"),
        patient_name=state["customer_name"],
        doctor_name=doctor.get("name", "Doctor"),
        date_str=state["selected_date"],
        time_str=state["selected_time"],
        booking_id=booking_id,
        doctor_email=doctor_email
    )

    state["messages"].append({
        "role": "assistant",
        "content": (
            f"Appointment Confirmed! 🎉\n\n"
            f"**Booking ID:** {booking_id}\n"
            f"**Doctor:** {doctor.get('name', '—')}\n"
            f"**Date:** {state['selected_date']}\n"
            f"**Time:** {state['selected_time']}\n\n"
            f"Thank you for choosing CarePlus Clinic."
        )
    })
    state["available_options"] = []
    return state


def cancelled_booking(state: BookingState) -> BookingState:
    state["messages"].append({
        "role": "assistant",
        "content": "Your booking has been cancelled. Type 'hi' to start a new booking whenever you're ready.",
        "options": ["Book Again"]
    })
    state["available_options"] = ["Book Again"]
    state["stage"] = "cancelled"
    return state


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_booking_graph():
    workflow = StateGraph(BookingState)

    # Bind the shared Groq client into sub-agents via partial
    _emergency = functools.partial(emergency_handler_node, groq_client=client)
    _reschedule = functools.partial(reschedule_handler_node, groq_client=client)

    workflow.add_node("greeting",          greeting_node)
    workflow.add_node("select_speciality", select_speciality_node)
    workflow.add_node("select_doctor",     select_doctor_node)
    workflow.add_node("select_date",       select_date_node)
    workflow.add_node("select_slot",       select_slot_node)
    workflow.add_node("confirm",           confirm_node)
    workflow.add_node("collect_details",   collect_details_node)
    workflow.add_node("completed",         completed_node)
    workflow.add_node("cancelled",         cancelled_booking)
    workflow.add_node("emergency_handler", _emergency)
    workflow.add_node("reschedule_handler", _reschedule)

    workflow.set_entry_point("greeting")

    EM = "emergency_handler"
    RS = "reschedule_handler"

    workflow.add_conditional_edges("greeting",          llm_router,
        {"greeting": "greeting", "select_speciality": "select_speciality",
         "cancelled": "cancelled", EM: EM, RS: RS})

    workflow.add_conditional_edges("select_speciality", llm_router,
        {"select_speciality": "select_speciality", "select_doctor": "select_doctor", EM: EM, RS: RS})

    workflow.add_conditional_edges("select_doctor",     llm_router,
        {"select_doctor": "select_doctor", "select_date": "select_date", EM: EM, RS: RS})

    workflow.add_conditional_edges("select_date",       llm_router,
        {"select_date": "select_date", "select_slot": "select_slot", EM: EM, RS: RS})

    workflow.add_conditional_edges("select_slot",       llm_router,
        {"select_slot": "select_slot", "confirm": "confirm", EM: EM, RS: RS})

    workflow.add_conditional_edges("confirm",           llm_router,
        {"confirm": "confirm", "collect_details": "collect_details",
         "cancelled": "cancelled", "select_slot": "select_slot", EM: EM, RS: RS})

    def _collect_router(s):
        return "completed" if (s.get("customer_name") and s.get("customer_phone") and s.get("customer_email")) else "collect_details"

    workflow.add_conditional_edges("collect_details",   _collect_router,
        {"collect_details": "collect_details", "completed": "completed"})

    def _sub_agent_router(s):
        return s.get("stage")

    workflow.add_conditional_edges("emergency_handler", _sub_agent_router,
        {"emergency_handler": "emergency_handler", "greeting": "greeting", "cancelled": "cancelled"})
        
    workflow.add_conditional_edges("reschedule_handler", _sub_agent_router,
        {"reschedule_handler": "reschedule_handler", "greeting": "greeting", "cancelled": "cancelled"})

    workflow.add_edge("completed", END)
    workflow.add_edge("cancelled", END)

    return workflow.compile(checkpointer=MemorySaver())


booking_graph = build_booking_graph()


# ---------------------------------------------------------------------------
# Entry point called by Streamlit
# ---------------------------------------------------------------------------

def process_message(
    state: BookingState,
    user_message: str,
    thread_id: str = "default_session",
) -> BookingState:
    config   = {"configurable": {"thread_id": thread_id}}
    snapshot = booking_graph.get_state(config)

    if snapshot.tasks and snapshot.tasks[0].interrupts:
        result = booking_graph.invoke(Command(resume=user_message), config=config)
    else:
        if user_message.lower() != "hi" or state["messages"]:
            if not state["messages"] or state["messages"][-1].get("content") != user_message:
                state["messages"].append({"role": "user", "content": user_message})
        result = booking_graph.invoke(state, config=config)

    # Sync interrupt payload to UI
    snapshot = booking_graph.get_state(config)
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        iv          = snapshot.tasks[0].interrupts[0].value
        msg_content = iv.get("content", "") if isinstance(iv, dict) else str(iv)
        options     = iv.get("options", []) if isinstance(iv, dict) else []

        if msg_content:
            last = result["messages"][-1].get("content", "") if result["messages"] else ""
            if last != msg_content:
                result["messages"].append({
                    "role": "assistant", "content": msg_content, "options": options
                })
            else:
                result["messages"][-1]["options"] = options

        result["available_options"] = options
    else:
        result.setdefault("available_options", [])

    return result