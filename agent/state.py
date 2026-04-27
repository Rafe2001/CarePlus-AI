from typing import Any, Dict, List, Optional, TypedDict

class BookingState(TypedDict):
    messages: List[Dict[str, Any]]
    stage: str
    selected_speciality: Optional[str]
    selected_doctor_id: Optional[int]
    selected_doctor: Optional[dict]
    selected_date: Optional[str]
    selected_time: Optional[str]
    customer_name: Optional[str]
    customer_age: Optional[int]
    customer_phone: Optional[str]
    customer_email: Optional[str]
    doctor_id: Optional[int]
    available_options: List[str]
    last_interrupt_message: Optional[str]
    booking_id: Optional[str]
    emergency_mode_active: bool
    reschedule_mode_active: bool
    ics_data: Optional[str]

def create_initial_stand() -> BookingState:
    return {
        "messages": [],
        "stage": "greeting",
        "selected_speciality": None,
        "selected_doctor_id": None,
        "selected_doctor": None,
        "selected_date": None,
        "selected_time": None,
        "customer_name": None,
        "customer_age": None,
        "customer_phone": None,
        "customer_email": None,
        "doctor_id": None,
        "available_options": [],
        "last_interrupt_message": None,
        "booking_id": None,
        "emergency_mode_active": False,
        "reschedule_mode_active": False,
        "ics_data": None,
    }
