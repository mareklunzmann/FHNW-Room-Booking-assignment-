"""Run: python objects_demo.py. No file is changed by this example.
Shows: JSON record -> Python object -> UML operation -> JSON record.
"""
import json
from domain import Booking, Room, Student
from storage import find_record, load_records


def main():
    # Constructor calls create objects from the data we read.
    student = Student(**find_record("students.json", "student_id", "S-100234"))
    room = Room(**find_record("rooms.json", "room_id", "R-421"))

    # The operation shown in our UML class Student: book(room, date, start, end): Booking
    booking = student.book(room, "B-DEMO", "2026-10-14", "12:00", "14:00",
                           "Gruppenarbeit Information Systems", 3)
    print(f"{student.first_name} {student.last_name} -> {room.room_name}")
    print(json.dumps(booking.to_record(), indent=2, ensure_ascii=False))

    # The operation of our UML class Booking: overlaps(other): Boolean
    existing = [Booking(**r) for r in load_records("bookings.json")]
    for other in existing:
        print(f"Overlaps {other.booking_id} ({other.start_time}-{other.end_time})? {booking.overlaps(other)}")
    print("Object created in memory; nothing saved. The API route POST /bookings adds the checks and saves.")


if __name__ == "__main__":
    main()
