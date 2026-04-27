"""
Emergency Agent — CarePlus Clinic
==================================
A self-contained sub-agent that handles medical emergencies.
It is imported by booking_agent.py and mounted as a node in the main graph.

Flow:
  1. First entry  → greet with emergency alert, ask for city/zip, interrupt
  2. User replies → run Groq tool-call to search_nearest_hospital
  3. Show results → interrupt again (loop) so user can ask follow-ups
  4. User says "cancel" or clicks "Cancel Emergency Mode" → exit to greeting
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from groq import Groq
from langgraph.types import interrupt

from tools.emergency_service import search_nearest_hospital

# ---------------------------------------------------------------------------
# Groq tool schema
# ---------------------------------------------------------------------------
HOSPITAL_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_nearest_hospital",
        "description": (
            "Searches the web for the nearest hospital or emergency room "
            "based on a city name or zip code."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or zip/postal code provided by the user."
                }
            },
            "required": ["location"]
        }
    }
}

_SYSTEM_PROMPT = (
    "You are an emergency medical assistant for CarePlus Clinic. "
    "The user may be experiencing a life-threatening situation. "
    "ALWAYS urge them to call emergency services (911 / 112) immediately. "
    "Use the search_nearest_hospital tool to find nearby ERs from their location. "
    "IMPORTANT: If you need to use a tool, you must call it directly. DO NOT output any conversational text before or after the tool call. "
    "Keep every text response short, clear, and urgent. "
    "Do NOT ask for appointment details — this is an emergency only context."
)

# ---------------------------------------------------------------------------
# Helper: run one Groq tool-calling round
# ---------------------------------------------------------------------------

def _run_emergency_search(client: Groq, recent_messages: List[Dict[str, Any]]) -> str:
    """
    Sends recent_messages to Groq with the hospital-search tool available.
    Executes the tool if called, returns the final assistant text.
    """
    api_messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for m in recent_messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=api_messages,
            tools=[HOSPITAL_SEARCH_TOOL],
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
                    if func_name == "search_nearest_hospital":
                        search_results = search_nearest_hospital(args.get("location", ""))
                        return f"Here is the nearest emergency room information based on your location:\n\n{search_results}"
                except Exception as parse_exc:
                    print(f"[EmergencyAgent] Regex parse error: {parse_exc}")
                    
        print(f"[EmergencyAgent] Groq API error: {exc}")
        return "🚨 Please call 911 or go to the nearest emergency room immediately!"

    choice = response.choices[0].message

    # No tool call → check if the LLM hallucinated the tool call in plain text
    if not choice.tool_calls:
        content = choice.content or "🚨 Please seek emergency help immediately!"
        if "<function=" in content:
            import re
            match = re.search(r'<function=([a-zA-Z0-9_]+).*?(\{.*?\})', content)
            if match:
                func_name = match.group(1)
                try:
                    args = json.loads(match.group(2))
                    if func_name == "search_nearest_hospital":
                        search_results = search_nearest_hospital(args.get("location", ""))
                        # Remove the hallucinated tag from the text and append the results
                        clean_content = re.sub(r'<function=.*?</function>', '', content).strip()
                        return f"{clean_content}\n\nHere is the nearest hospital information:\n{search_results}"
                except Exception as parse_exc:
                    print(f"[EmergencyAgent] Text Regex parse error: {parse_exc}")
        return content

    # Execute every tool call (usually just one)
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
        if tc.function.name == "search_nearest_hospital":
            try:
                args = json.loads(tc.function.arguments)
                search_results = search_nearest_hospital(args["location"])
            except Exception as exc:
                print(f"[EmergencyAgent] Tool execution error: {exc}")
                search_results = "Could not retrieve results. Please call 911."

            api_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": search_results
            })

    # Second Groq call — synthesise results into a human reply
    try:
        final = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=api_messages,
            max_tokens=400,
        )
        return final.choices[0].message.content or "🚨 Please seek emergency help now!"
    except Exception as exc:
        print(f"[EmergencyAgent] Final synthesis error: {exc}")
        return "🚨 Please call 911 or go to the nearest emergency room immediately!"


# ---------------------------------------------------------------------------
# Public node function — mounted into the main LangGraph
# ---------------------------------------------------------------------------

def emergency_handler_node(state: dict, *, groq_client: Groq) -> dict:
    """
    LangGraph node for emergency handling.

    State keys read/written:
      - stage                 (set to "emergency_handler")
      - emergency_mode_active (bool flag)
      - messages              (appended to)
      - available_options     (set for Streamlit quick-reply buttons)

    The node uses ONE interrupt per execution (LangGraph constraint):
      - First entry:  show alert message → interrupt for location
      - Subsequent:   user replied with location → search → interrupt for follow-up
    """
    state["stage"] = "emergency_handler"
    CANCEL_OPTS = ["Cancel Emergency Mode"]

    if not state.get("emergency_mode_active"):
        state["emergency_mode_active"] = True
        alert = (
            "🚨 **MEDICAL EMERGENCY DETECTED.**\n\n"
            "Please call **911** (or your local emergency number) immediately "
            "if this is life-threatening!\n\n"
            "To help further, please tell me your **city or zip code** and I will "
            "find the nearest emergency room for you."
        )
        state["messages"].append({
            "role": "assistant",
            "content": alert,
            "options": CANCEL_OPTS
        })
        state["available_options"] = CANCEL_OPTS
    else:
        # Subsequent loop: user has replied to our previous prompt
        last_role = state["messages"][-1]["role"] if state["messages"] else ""
        if last_role == "user":
            user_msg = state["messages"][-1]["content"]
            if "cancel" in user_msg.lower():
                return _exit_emergency(state)
                
            bot_reply = _run_emergency_search(groq_client, state["messages"][-4:])
            state["messages"].append({
                "role": "assistant",
                "content": bot_reply,
                "options": CANCEL_OPTS
            })
            state["available_options"] = CANCEL_OPTS

    # Now the last message is guaranteed to be from the assistant. We interrupt.
    last_bot_msg = state["messages"][-1]["content"]
    user_input = interrupt({"content": last_bot_msg, "options": CANCEL_OPTS})
    
    state["messages"].append({"role": "user", "content": user_input})
    
    if "cancel" in user_input.lower():
        return _exit_emergency(state)

    return state


def _exit_emergency(state: dict) -> dict:
    """Clean up emergency state and return to greeting."""
    state["emergency_mode_active"] = False
    state["stage"] = "greeting"
    goodbye = (
        "Emergency mode cancelled. I hope you're safe. "
        "You can continue booking an appointment or type 'hi' to start over."
    )
    state["messages"].append({
        "role": "assistant",
        "content": goodbye,
        "options": ["Book Appointment"]
    })
    state["available_options"] = ["Book Appointment"]
    return state