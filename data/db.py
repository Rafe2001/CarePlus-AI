import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger("careplus.db")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def _mask_db_url(url):
    if not url:
        return "<missing>"
    if "@" not in url:
        return url
    prefix, suffix = url.split("@", 1)
    if "://" in prefix:
        scheme, rest = prefix.split("://", 1)
        return f"{scheme}://***:***@{suffix}"
    return f"***:***@{suffix}"


def get_connection():
    logger.info("Opening database connection to %s", _mask_db_url(DATABASE_URL))
    conn = psycopg2.connect(
        os.getenv("DATABASE_URL"),
        sslmode="require"
    )
    params = conn.get_dsn_parameters()
    logger.info(
        "Connected to Postgres host=%s dbname=%s user=%s",
        params.get("host", "?"),
        params.get("dbname", "?"),
        params.get("user", "?"),
    )
    return conn
    
def init_db():
    logger.info("Initializing database schema")
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        logger.info("Ensuring table exists: doctors")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctors_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            office_hours TEXT NOT NULL,
            email TEXT
        )
        """)

        logger.info("Ensuring table exists: patients")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patients_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            phone_no TEXT NOT NULL,
            email TEXT
        )
        """)

        logger.info("Ensuring table exists: bookings")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients (patients_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors (doctors_id)
        )
        """)

        doctors = [
            (1, 'Dr. John Smith', 'Cardiologist', '9:00 AM - 5:00 PM', 'dr.john.smith@khanplus.com'),
            (2, 'Dr. Emily Davis', 'Dermatologist', '10:00 AM - 6:00 PM', 'dr.emily.davis@khanplus.com'),
            (3, 'Dr. Michael Brown', 'Pediatrician', '8:00 AM - 4:00 PM', 'dr.michael.brown@khanplus.com'),
            (4, 'Dr. Sarah Johnson', 'Orthopedic Surgeon', '11:00 AM - 7:00 PM', 'dr.sarah.johnson@khanplus.com'),
            (5, 'Dr. David Wilson', 'Neurologist', '9:30 AM - 5:30 PM', 'dr.david.wilson@khanplus.com')
        ]

        logger.info("Seeding %d doctor records", len(doctors))
        for doc in doctors:
            cur.execute("""
            INSERT INTO doctors (doctors_id, name, specialization, office_hours, email)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (doctors_id) DO UPDATE SET email = EXCLUDED.email
            """, doc)

        conn.commit()
        logger.info("Database initialization complete")
    except Exception:
        logger.exception("Database initialization failed")
        raise
    finally:
        if conn is not None:
            conn.close()
            logger.info("Database connection closed")


# -------------------- DOCTOR FUNCTIONS --------------------

def get_all_doctors():
    logger.info("Query: get_all_doctors")
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM doctors")
        result = cur.fetchall()
        logger.info("Query complete: get_all_doctors -> %d rows", len(result))
        return result
    except Exception:
        logger.exception("Query failed: get_all_doctors")
        raise
    finally:
        conn.close()


def get_doctors_by_speciality(specialization):
    logger.info("Query: get_doctors_by_speciality specialisation=%s", specialization)
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM doctors 
            WHERE LOWER(specialization) = LOWER(%s)
        """, (specialization,))
        result = cur.fetchall()
        logger.info("Query complete: get_doctors_by_speciality -> %d rows", len(result))
        return result
    except Exception:
        logger.exception("Query failed: get_doctors_by_speciality")
        raise
    finally:
        conn.close()


def get_doctor_by_id(doctor_id):
    logger.info("Query: get_doctor_by_id doctor_id=%s", doctor_id)
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM doctors WHERE doctors_id = %s", (doctor_id,))
        result = cur.fetchone()
        logger.info("Query complete: get_doctor_by_id -> %s", "hit" if result else "miss")
        return result
    except Exception:
        logger.exception("Query failed: get_doctor_by_id")
        raise
    finally:
        conn.close()


# -------------------- PATIENT FUNCTIONS --------------------

def create_customer(customer_id, name, age, phone, email=None):
    logger.info("Mutation: create_customer customer_id=%s phone=%s", customer_id, phone)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO patients (patients_id, name, age, phone_no, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (customer_id, name, age, phone, email))
        conn.commit()
        logger.info("Mutation complete: create_customer")
    except Exception:
        logger.exception("Mutation failed: create_customer")
        raise
    finally:
        conn.close()


def get_customer_by_phone(phone):
    logger.info("Query: get_customer_by_phone phone=%s", phone)
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM patients WHERE phone_no = %s", (phone,))
        result = cur.fetchone()
        logger.info("Query complete: get_customer_by_phone -> %s", "hit" if result else "miss")
        return result
    except Exception:
        logger.exception("Query failed: get_customer_by_phone")
        raise
    finally:
        conn.close()


# -------------------- BOOKING FUNCTIONS --------------------

def create_booking(booking_id, patient_id, doctor_id, appointment_date, appointment_time, status="confirmed"):
    logger.info(
        "Mutation: create_booking booking_id=%s patient_id=%s doctor_id=%s date=%s time=%s",
        booking_id, patient_id, doctor_id, appointment_date, appointment_time
    )
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bookings (booking_id, patient_id, doctor_id, appointment_date, appointment_time, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (booking_id, patient_id, doctor_id, appointment_date, appointment_time, status))
        conn.commit()
        logger.info("Mutation complete: create_booking")
    except Exception:
        logger.exception("Mutation failed: create_booking")
        raise
    finally:
        conn.close()


def get_bookings_by_doctor_and_date(doctor_id, date):
    logger.info("Query: get_bookings_by_doctor_and_date doctor_id=%s date=%s", doctor_id, date)
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT appointment_time FROM bookings 
            WHERE doctor_id = %s AND appointment_date = %s AND status = %s
        """, (doctor_id, date, "confirmed"))
        result = cur.fetchall()
        logger.info("Query complete: get_bookings_by_doctor_and_date -> %d rows", len(result))
        return result
    except Exception:
        logger.exception("Query failed: get_bookings_by_doctor_and_date")
        raise
    finally:
        conn.close()


def get_booking_by_id(booking_id):
    logger.info("Query: get_booking_by_id booking_id=%s", booking_id)
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
        result = cur.fetchone()
        logger.info("Query complete: get_booking_by_id -> %s", "hit" if result else "miss")
        return result
    except Exception:
        logger.exception("Query failed: get_booking_by_id")
        raise
    finally:
        conn.close()


def cancel_booking(booking_id):
    logger.info("Mutation: cancel_booking booking_id=%s", booking_id)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE bookings SET status = 'cancelled' WHERE booking_id = %s", (booking_id,))
        conn.commit()
        logger.info("Mutation complete: cancel_booking")
    except Exception:
        logger.exception("Mutation failed: cancel_booking")
        raise
    finally:
        conn.close()


def update_booking(booking_id, appointment_date, appointment_time):
    logger.info(
        "Mutation: update_booking booking_id=%s date=%s time=%s",
        booking_id, appointment_date, appointment_time
    )
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE bookings 
            SET appointment_date = %s, appointment_time = %s 
            WHERE booking_id = %s
        """, (appointment_date, appointment_time, booking_id))
        conn.commit()
        logger.info("Mutation complete: update_booking")
    except Exception:
        logger.exception("Mutation failed: update_booking")
        raise
    finally:
        conn.close()


def get_bookings_by_patient_id(patient_id):
    logger.info("Query: get_bookings_by_patient_id patient_id=%s", patient_id)
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM bookings 
            WHERE patient_id = %s AND status = %s
        """, (patient_id, "confirmed"))
        result = cur.fetchall()
        logger.info("Query complete: get_bookings_by_patient_id -> %d rows", len(result))
        return result
    except Exception:
        logger.exception("Query failed: get_bookings_by_patient_id")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
