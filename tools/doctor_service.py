from data.db import get_all_doctors, get_doctors_by_speciality, get_doctor_by_id, get_customer_by_phone, get_bookings_by_doctor_and_date 

# Get specialist list
def get_specialist_list():
    doctors = get_all_doctors()
    specialities = set()
    for doctor in doctors:
        specialities.add(doctor[2])  # Assuming specialization is the third column
    return list(specialities)

# choose a doctor based on speciality

def get_doctors_info(specialization):
    doctors = get_doctors_by_speciality(specialization)
    if doctors:
        doc = doctors[0]
        return {
            "doctors_id": doc[0],
            "doctor_id": doc[0],
            "name": doc[1],
            "specialization": doc[2],
            "office_hours": doc[3],
            "email": doc[4] if len(doc) > 4 else None
        }
    return None

def find_doctor_by_id(doctor_id):
    doctor = get_doctor_by_id(doctor_id)
    if doctor:
        return {
            "doctors_id": doctor[0],
            "doctor_id": doctor[0],
            "name": doctor[1],
            "specialization": doctor[2],
            "office_hours": doctor[3],
            "email": doctor[4] if len(doctor) > 4 else None
        }
    return None

def find_customer_by_phone(phone):
    customer = get_customer_by_phone(phone)
    return customer

# generate time slot
from datetime import datetime, timedelta

def generate_time_slot(office_hours, slot_duration=30):
    # Example: "9:00 AM - 5:00 PM"
    start_str, end_str = office_hours.split(" - ")

    start_time = datetime.strptime(start_str.strip(), "%I:%M %p")
    end_time = datetime.strptime(end_str.strip(), "%I:%M %p")

    slots = []
    current_time = start_time

    while current_time < end_time:
        next_time = current_time + timedelta(minutes=slot_duration)
        slot = f"{current_time.strftime('%I:%M %p')} - {next_time.strftime('%I:%M %p')}"
        slots.append(slot)
        current_time = next_time

    return slots
