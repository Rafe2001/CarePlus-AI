import os
import sqlite3
from datetime import datetime, timedelta

db_path = os.path.join(os.path.dirname(__file__), 'data.db')

def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    #doctor's table
    c.execute('''CREATE TABLE IF NOT EXISTS doctors
                 (doctors_id INTEGER PRIMARY KEY,
                  name TEXT NOT NULL,
                  specialization TEXT NOT NULL,
                  office_hours TEXT NOT NULL,
                  email TEXT)''')
    #patients table
    c.execute('''CREATE TABLE IF NOT EXISTS patients
                 (patients_id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  age INTEGER NOT NULL,
                  phone_no TEXT NOT NULL,
                  email TEXT)''')
                  
    # Attempt to add columns if tables already existed
    try:
        c.execute("ALTER TABLE doctors ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE patients ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass
    #booking table
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (booking_id TEXT PRIMARY KEY,
                  patient_id TEXT NOT NULL,
                  doctor_id TEXT NOT NULL,
                  appointment_date TEXT NOT NULL,
                  appointment_time TEXT NOT NULL,
                  status TEXT NOT NULL,
                  FOREIGN KEY (patient_id) REFERENCES patients (patients_id),
                  FOREIGN KEY (doctor_id) REFERENCES doctors (doctors_id)
                  )''')
    
    #Insert same data of doctors
    
    doctors = [
        (1, 'Dr. John Smith', 'Cardiologist', '9:00 AM - 5:00 PM', 'dr.john.smith@khanplus.com'),
        (2, 'Dr. Emily Davis', 'Dermatologist', '10:00 AM - 6:00 PM', 'dr.emily.davis@khanplus.com'),
        (3, 'Dr. Michael Brown', 'Pediatrician', '8:00 AM - 4:00 PM', 'dr.michael.brown@khanplus.com'),
        (4, 'Dr. Sarah Johnson', 'Orthopedic Surgeon', '11:00 AM - 7:00 PM', 'dr.sarah.johnson@khanplus.com'),
        (5, 'Dr. David Wilson', 'Neurologist', '9:30 AM - 5:30 PM', 'dr.david.wilson@khanplus.com')
    ]
    
    for doc in doctors:
        c.execute("INSERT OR IGNORE INTO doctors (doctors_id, name, specialization, office_hours, email) VALUES (?, ?, ?, ?, ?)", doc)
        # Update existing doctors to ensure they have an email
        c.execute("UPDATE doctors SET email = ? WHERE doctors_id = ?", (doc[4], doc[0]))
    conn.commit()
    conn.close()
    
    
def get_all_doctors():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM doctors")
    doctors = c.fetchall()
    conn.close()
    return doctors

def get_doctors_by_speciality(specialization):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM doctors WHERE lower(specialization) = lower(?)", (specialization,))
    doctors = c.fetchall()
    conn.close()
    return doctors

def get_doctor_by_id(doctor_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM doctors WHERE doctors_id = ?", (doctor_id,))
    doctor = c.fetchone()
    conn.close()
    return doctor

def create_customer(customer_id, name, age, phone, email=None):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO patients (patients_id, name, age, phone_no, email) VALUES (?, ?, ?, ?, ?)", (customer_id, name, age, phone, email))
    conn.commit()
    conn.close()

def get_customer_by_phone(phone):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM patients WHERE phone_no = ?", (phone,))
    customer = c.fetchone()
    conn.close()
    return customer
    
    
def create_booking(booking_id, patient_id, doctor_id, appointment_date, appointment_time, status="confirmed"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO bookings (booking_id, patient_id, doctor_id, appointment_date, appointment_time, status) VALUES (?, ?, ?, ?, ?, ?)", (booking_id, patient_id, doctor_id, appointment_date, appointment_time, status))
    conn.commit()
    conn.close()

def get_bookings_by_doctor_and_date(doctor_id, date):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT appointment_time FROM bookings WHERE doctor_id = ? AND appointment_date = ? AND status = ?", (doctor_id, date, "confirmed"))
    bookings = c.fetchall()
    conn.close()
    return bookings

def get_booking_by_id(booking_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
    booking = c.fetchone()
    conn.close()
    return booking

def cancel_booking(booking_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,))
    conn.commit()
    conn.close()

def update_booking(booking_id, appointment_date, appointment_time):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE bookings SET appointment_date = ?, appointment_time = ? WHERE booking_id = ?", (appointment_date, appointment_time, booking_id))
    conn.commit()
    conn.close()

def get_bookings_by_patient_id(patient_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM bookings WHERE patient_id = ? AND status = 'confirmed'", (patient_id,))
    bookings = c.fetchall()
    conn.close()
    return bookings

if __name__ == '__main__':
    init_db()