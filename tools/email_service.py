import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from ics import Calendar, Event

def generate_ics_file(patient_name, doctor_name, date_str, time_str):
    c = Calendar()
    e = Event()
    e.name = f"Medical Appointment with {doctor_name}"
    
    try:
        # parse date and time (e.g. "2026-04-26" and "10:00 AM - 10:30 AM")
        start_time_str = time_str.split(" - ")[0].strip()
        start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %I:%M %p")
        end_dt = start_dt + timedelta(minutes=30)
        
        # ics expects timezone aware or specific format. For simplicity, format to string
        e.begin = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        e.end = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as err:
        print(f"Error parsing date/time for ICS: {err}")
        # fallback to all day event
        e.begin = date_str
        
    e.description = f"Appointment for {patient_name} with {doctor_name} at KhanPlus Clinic."
    e.location = "KhanPlus Clinic, 123 Health Ave."
    
    c.events.add(e)
    return str(c)

def send_confirmation_email(to_email, patient_name, doctor_name, date_str, time_str, booking_id, doctor_email=None):
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")
    
    # Generate ICS
    ics_content = generate_ics_file(patient_name, doctor_name, date_str, time_str)
    
    if not doctor_email:
        doctor_email = f"{doctor_name.lower().replace(' ', '.').replace('dr.', 'dr')}@khanplus.com"
    
    # If no email configured, just print and return
    if not sender_email or not sender_password:
        print(f"--- MOCK EMAILS SENT ---")
        print(f"Patient Email To: {to_email}")
        print(f"Doctor Email To: {doctor_email}")
        print(f"Attachment: invite.ics attached to both.\n")
        return True
        
    try:
        # 1. Send to Patient
        msg_patient = EmailMessage()
        msg_patient['Subject'] = f"Booking Confirmation: KhanPlus Clinic ({booking_id})"
        msg_patient['From'] = sender_email
        msg_patient['To'] = to_email
        
        body_patient = f"Dear {patient_name},\n\nYour appointment at KhanPlus Clinic has been confirmed!\n\nBooking ID: {booking_id}\nDoctor: {doctor_name}\nDate: {date_str}\nTime: {time_str}\n\nPlease find your calendar invite attached.\n\nBest regards,\nKhanPlus Clinic"
        msg_patient.set_content(body_patient)
        msg_patient.add_attachment(ics_content.encode('utf-8'), maintype='text', subtype='calendar', filename='invite.ics')
        
        # 2. Send to Doctor
        msg_doctor = EmailMessage()
        msg_doctor['Subject'] = f"New Patient Appointment: {patient_name} ({booking_id})"
        msg_doctor['From'] = sender_email
        msg_doctor['To'] = doctor_email
        
        body_doctor = f"Dear {doctor_name},\n\nYou have a new appointment booked.\n\nPatient: {patient_name}\nBooking ID: {booking_id}\nDate: {date_str}\nTime: {time_str}\n\nPlease find the calendar invite attached.\n\nKhanPlus Clinic System"
        msg_doctor.set_content(body_doctor)
        msg_doctor.add_attachment(ics_content.encode('utf-8'), maintype='text', subtype='calendar', filename='invite.ics')
        
        # Send using Gmail SMTP (can be modified for others)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg_patient)
            server.send_message(msg_doctor)
            
        print(f"Emails successfully sent to {to_email} and {doctor_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
