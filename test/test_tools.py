from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.db import init_db
from tools.doctor_service import get_specialist_list, find_doctors_by_speciality, find_doctor_by_id, find_customer_by_phone, generate_time_slot
from tools.booking_service import get_or_create_customer, get_available_slots, confirm_booking, get_booking_details


specialists = get_specialist_list()

print("Specialist List:")
i = 0
for s in specialists:
    i += 1
    print(f" {i}. {s}")

slots = generate_time_slot("9:00 AM - 5:00 PM")
print(slots)

#confirm booking 
booking_id = confirm_booking("DOC-001", "John Doe", "1234567890", "2024-07-01", "10:00 AM - 10:30 AM")
print(f"Booking ID: {booking_id}")