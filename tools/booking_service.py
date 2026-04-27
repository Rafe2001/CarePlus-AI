import uuid
from datetime import datetime, timedelta
from data.db import get_all_doctors, get_bookings_by_doctor_and_date, get_doctor_by_id, get_doctors_by_speciality, create_booking, get_booking_by_id, create_customer, get_customer_by_phone
from tools.doctor_service import generate_time_slot 

def get_or_create_customer(name, phone, email=None):
    customer = get_customer_by_phone(phone)
    if customer:
        return customer[0] 
    
    customer_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"
    create_customer(customer_id, name, 0, phone, email)
    return customer_id

def get_available_slots(doctor_id, date):
    appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
    all_slots = generate_time_slot(get_doctor_by_id(doctor_id)[3])  # office_hours is the 4th column
    booked_items = get_bookings_by_doctor_and_date(doctor_id, date)
    # filter out booked slots
    booked_slots = [booking[0] for booking in booked_items]  # appointment_time is the first column
    available_slots = [slot for slot in all_slots if slot not in booked_slots]  
    return available_slots

def confirm_booking(doctor_id, patient_name, patient_phone, date, time, patient_email=None):
    customer_id = get_or_create_customer(patient_name, patient_phone, patient_email)
    booking_id = f"BOOK-{uuid.uuid4().hex[:6].upper()}"
    create_booking(booking_id, customer_id, doctor_id, date, time)
    return booking_id

def get_booking_details(booking_id):
    booking = get_booking_by_id(booking_id)
    if booking:
        return {
            "booking_id": booking[0],
            "patient_id": booking[1],
            "doctor_id": booking[2],
            "appointment_date": booking[3],
            "appointment_time": booking[4],
            "status": booking[5]
        }
    return None