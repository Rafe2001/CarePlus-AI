import json
from typing import Any, Dict, List
from groq import Groq
from langgraph.types import interrupt

from data.db import cancel_booking, update_booking, get_customer_by_phone, get_bookings_by_patient_id, get_doctor_by_id
from tools.doctor_service import generate_time_slot

RESCHEDULE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_bookings",
            "description": "Looks up a patient's active appointments using their phone number.",
            "parameters": {
                "type": "object",
                "properties": {"phone": {"type": "string"}},
                "required": ["phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancels a specific appointment by booking ID.",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "string"}},
                "required": ["booking_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Gets available time slots for a doctor on a specific date (YYYY-MM-DD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string", "description": "The ID of the doctor (e.g. '3')"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["doctor_id", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_appointment",
            "description": "Changes the date and time of an existing appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string"},
                    "new_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "new_time": {"type": "string"}
                },
                "required": ["booking_id", "new_date", "new_time"]
            }
        }
    }
]

def _tool_lookup_bookings(phone: str) -> str:
    # Clean phone number
    digits = ''.join(filter(str.isdigit, phone))
    customer = get_customer_by_phone(digits)
    if not customer:
        return f"No patient found with phone number {phone}."
    
    patient_id = customer["patients_id"] if isinstance(customer, dict) else customer[0]
    bookings = get_bookings_by_patient_id(patient_id)
    if not bookings:
        patient_name = customer["name"] if isinstance(customer, dict) else customer[1]
        return f"No active appointments found for patient {patient_name}."
        
    patient_name = customer["name"] if isinstance(customer, dict) else customer[1]
    res = f"Found {len(bookings)} active appointments for {patient_name}:\n"
    for b in bookings:
        doctor_id = b["doctor_id"] if isinstance(b, dict) else b[2]
        doctor = get_doctor_by_id(doctor_id)
        doc_name = doctor["name"] if isinstance(doctor, dict) else doctor[1] if doctor else "Unknown Doctor"
        booking_id = b["booking_id"] if isinstance(b, dict) else b[0]
        appointment_date = b["appointment_date"] if isinstance(b, dict) else b[3]
        appointment_time = b["appointment_time"] if isinstance(b, dict) else b[4]
        res += f"- Booking ID: {booking_id}, Doctor: {doc_name}, Date: {appointment_date}, Time: {appointment_time} (DocID: {doctor_id})\n"
    return res

def _tool_cancel_appointment(booking_id: str) -> str:
    try:
        cancel_booking(booking_id)
        return f"Appointment {booking_id} has been successfully cancelled."
    except Exception as e:
        return f"Error cancelling appointment: {e}"

def _tool_get_available_slots(doctor_id: str, date: str) -> str:
    try:
        doctor_id_int = int(doctor_id)
    except ValueError:
        return "Invalid doctor ID format."
        
    doctor = get_doctor_by_id(doctor_id_int)
    if not doctor:
        return "Doctor not found."
    office_hours = doctor["office_hours"] if isinstance(doctor, dict) else doctor[3]
    slots = generate_time_slot(office_hours)
    return f"Available slots for {date}: {', '.join(slots)}"

def _tool_update_appointment(booking_id: str, new_date: str, new_time: str) -> str:
    try:
        update_booking(booking_id, new_date, new_time)
        return f"Appointment {booking_id} successfully rescheduled to {new_date} at {new_time}."
    except Exception as e:
        return f"Error updating appointment: {e}"

_SYSTEM_PROMPT = (
    "You are a friendly Rescheduling & Cancellation Assistant for KhanPlus Clinic. "
    "Your goal is to help users find their appointments using their phone number, "
    "and then either cancel them or reschedule them to a new date/time. "
    "1. If you DO NOT have the user's phone number, you MUST ask for it in plain text. DO NOT call any tools until they reply with their number. "
    "2. Once you have the phone number, use lookup_bookings to find their appointments. The result includes the doctor_id (DocID). "
    "3. To cancel, use cancel_appointment. "
    "4. To reschedule, first use get_available_slots (using the doctor_id from step 2) to find times on the new date, "
    "then ask the user to pick one, then use update_appointment. "
    "IMPORTANT: If you need to use a tool, you must call it directly. DO NOT output any conversational text before or after the tool call. "
    "Be concise and helpful. When a task is complete, ask if there is anything else."
)

def _run_reschedule_agent(client: Groq, recent_messages: List[Dict[str, Any]]) -> str:
    api_messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for m in recent_messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=api_messages,
            tools=RESCHEDULE_TOOLS,
            tool_choice="auto",
            max_tokens=400,
        )
    except Exception as exc:
        err_str = str(exc)
        if "<function=" in err_str:
            import re
            match = re.search(r'<function=([a-zA-Z0-9_]+).*?(\{.*?\})', err_str)
            if match:
                func_name = match.group(1)
                try:
                    args = json.loads(match.group(2))
                    if func_name == "lookup_bookings":
                        return _tool_lookup_bookings(args.get("phone", ""))
                    elif func_name == "cancel_appointment":
                        return _tool_cancel_appointment(args.get("booking_id", ""))
                    elif func_name == "get_available_slots":
                        return _tool_get_available_slots(args.get("doctor_id", ""), args.get("date", ""))
                    elif func_name == "update_appointment":
                        return _tool_update_appointment(args.get("booking_id", ""), args.get("new_date", ""), args.get("new_time", ""))
                except Exception as parse_exc:
                    print(f"[RescheduleAgent] Regex parse error: {parse_exc}")
                    
        print(f"[RescheduleAgent] Groq API error: {exc}")
        return "I'm having trouble connecting to the scheduling system right now."

    choice = response.choices[0].message
    
    if not choice.tool_calls:
        content = choice.content or "How can I help you with your appointment?"
        if "<function=" in content:
            import re
            match = re.search(r'<function=([a-zA-Z0-9_]+).*?(\{.*?\})', content)
            if match:
                func_name = match.group(1)
                try:
                    args = json.loads(match.group(2))
                    if func_name == "lookup_bookings":
                        res = _tool_lookup_bookings(args.get("phone", ""))
                    elif func_name == "cancel_appointment":
                        res = _tool_cancel_appointment(args.get("booking_id", ""))
                    elif func_name == "get_available_slots":
                        res = _tool_get_available_slots(args.get("doctor_id", ""), args.get("date", ""))
                    elif func_name == "update_appointment":
                        res = _tool_update_appointment(args.get("booking_id", ""), args.get("new_date", ""), args.get("new_time", ""))
                    else:
                        res = ""
                    clean_content = re.sub(r'<function=.*?</function>', '', content).strip()
                    return f"{clean_content}\n\n{res}"
                except Exception as parse_exc:
                    print(f"[RescheduleAgent] Text Regex parse error: {parse_exc}")
        return content

    api_messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in choice.tool_calls
        ]
    })

    for tc in choice.tool_calls:
        try:
            args = json.loads(tc.function.arguments)
            if tc.function.name == "lookup_bookings":
                result = _tool_lookup_bookings(args["phone"])
            elif tc.function.name == "cancel_appointment":
                result = _tool_cancel_appointment(args["booking_id"])
            elif tc.function.name == "get_available_slots":
                result = _tool_get_available_slots(args["doctor_id"], args["date"])
            elif tc.function.name == "update_appointment":
                result = _tool_update_appointment(args["booking_id"], args["new_date"], args["new_time"])
            else:
                result = "Unknown tool."
        except Exception as exc:
            print(f"[RescheduleAgent] Tool error: {exc}")
            result = "Error executing action."

        api_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": tc.function.name,
            "content": result
        })

    try:
        final = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=api_messages,
            max_tokens=400,
        )
        return final.choices[0].message.content or "Action completed."
    except Exception as exc:
        print(f"[RescheduleAgent] Synthesis error: {exc}")
        return "Action completed, but I couldn't generate a response."

def reschedule_handler_node(state: dict, *, groq_client: Groq) -> dict:
    state["stage"] = "reschedule_handler"
    CANCEL_OPTS = ["Return to Main Menu"]

    last_role = state["messages"][-1]["role"] if state["messages"] else ""

    # If the last message was from the user, the agent needs to respond to it.
    if last_role == "user":
        user_msg = state["messages"][-1]["content"]
        if "return" in user_msg.lower() or "main menu" in user_msg.lower():
            return _exit_reschedule(state)
            
        # Hardcode the first response to prevent LLM tool hallucination without a phone number
        if "manage" in user_msg.lower() and not state.get("reschedule_mode_active"):
            state["reschedule_mode_active"] = True
            bot_reply = "To manage your appointments, I'll need to look up your bookings. Could you please provide your phone number?"
        else:
            bot_reply = _run_reschedule_agent(groq_client, state["messages"][-4:])
            
        state["messages"].append({
            "role": "assistant",
            "content": bot_reply,
            "options": CANCEL_OPTS
        })
        state["available_options"] = CANCEL_OPTS

    # Now the last message in the state is guaranteed to be from the assistant.
    # We must pause execution and wait for the user to reply.
    last_bot_msg = state["messages"][-1]["content"]
    user_input = interrupt({"content": last_bot_msg, "options": CANCEL_OPTS})
    
    # User has replied. Append their message and return so the graph can cycle.
    state["messages"].append({"role": "user", "content": user_input})
    
    if "return" in user_input.lower() or "main menu" in user_input.lower():
        return _exit_reschedule(state)

    return state

def _exit_reschedule(state: dict) -> dict:
    state["reschedule_mode_active"] = False
    state["stage"] = "greeting"
    state["messages"].append({
        "role": "assistant",
        "content": "Returning to the main menu. How can I assist you today?",
        "options": ["Book Appointment", "Manage Appointments"]
    })
    state["available_options"] = ["Book Appointment", "Manage Appointments"]
    return state
