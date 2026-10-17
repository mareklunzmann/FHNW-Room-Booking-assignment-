"""The UML classes of the FHNW Room Booking System (application / domain logic).
These ordinary Python classes do not depend on FastAPI.
Attributes store state; methods define behaviour (our business rules).

Business rules from our model (Milestone 1, refined after coaching):
  1. No double booking: active bookings of the same room must not overlap.
     Half-open slots: startA < endB AND startB < endA, so 10-12 and 12-14 are both allowed.
  2. Valid time range: start_time strictly before end_time (one calendar day).
  3. Soft cancellation: status becomes CANCELLED; the record stays but no longer blocks the room.
  4. Allowed bookings: only inside the room's opening hours for that weekday and not on a holiday.
  5. (Proposal) participants must not exceed the room's capacity.
"""
from datetime import datetime

ACTIVE = "ACTIVE"          # enumeration BookingStatus
CANCELLED = "CANCELLED"


def parse_time(value: str):
    """'12:00' -> a time object that can be compared; ValueError for '25:00'."""
    return datetime.strptime(value, "%H:%M").time()


def parse_date(value: str):
    """'2026-10-14' -> a date object; ValueError for '2026-02-30'."""
    return datetime.strptime(value, "%Y-%m-%d").date()


class Building:
    def __init__(self, building_id: str, name: str, street: str, street_no: str | None,
                 postal_code: str, city: str, contact_number: str):
        self.building_id = building_id
        self.name = name
        self.street = street
        self.street_no = street_no            # optional [0..1]
        self.postal_code = postal_code
        self.city = city
        self.contact_number = contact_number


class CalendarDay:
    """Our ER entity 'Date'. Renamed because Date is already a UML data type."""

    def __init__(self, date: str, weekday: int, is_holiday: bool):
        self.date = date
        self.weekday = weekday                # 1 = Monday ... 7 = Sunday
        self.is_holiday = is_holiday

    @classmethod
    def for_date(cls, date: str, records: list):
        """Use the stored day if it exists; otherwise derive the weekday (normal day)."""
        for record in records:
            if record["date"] == date:
                return cls(record["date"], record["weekday"], record["is_holiday"])
        return cls(date, parse_date(date).isoweekday(), False)


class Availability:
    def __init__(self, availability_id: str, room_id: str, weekday: int,
                 opening_time: str, closing_time: str):
        self.availability_id = availability_id
        self.room_id = room_id
        self.weekday = weekday
        self.opening_time = opening_time
        self.closing_time = closing_time

    def covers(self, start_time: str, end_time: str) -> bool:
        """Rule 4: the whole slot lies inside the opening hours."""
        return (parse_time(self.opening_time) <= parse_time(start_time)
                and parse_time(end_time) <= parse_time(self.closing_time))


class Booking:
    """Associative entity between Student and Room."""

    def __init__(self, booking_id: str, student_id: str, room_id: str, date: str,
                 start_time: str, end_time: str, event_name: str | None = None,
                 participants: int = 1, status: str = ACTIVE, created_at: str | None = None):
        self.booking_id = booking_id
        self.student_id = student_id
        self.room_id = room_id
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.event_name = event_name          # optional [0..1]
        self.participants = participants
        self.status = status
        self.created_at = created_at

    def is_active(self) -> bool:
        return self.status == ACTIVE

    def overlaps(self, other) -> bool:
        """Rule 1: same room, same day, both active and the time slots intersect."""
        if self.room_id != other.room_id or self.date != other.date:
            return False
        if not (self.is_active() and other.is_active()):
            return False
        return (parse_time(self.start_time) < parse_time(other.end_time)
                and parse_time(other.start_time) < parse_time(self.end_time))

    def cancel(self):
        """Rule 3: soft cancellation - the record stays for reporting."""
        self.status = CANCELLED

    def to_record(self):
        # A method is behaviour; it is not stored as a JSON field.
        return {
            "booking_id": self.booking_id,
            "student_id": self.student_id,
            "room_id": self.room_id,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "event_name": self.event_name,
            "participants": self.participants,
            "status": self.status,
            "created_at": self.created_at,
        }


class Room:
    def __init__(self, room_id: str, building_id: str, room_name: str, floor: str, capacity: int):
        self.room_id = room_id
        self.building_id = building_id
        self.room_name = room_name
        self.floor = floor
        self.capacity = capacity

    def is_available(self, date: str, start_time: str, end_time: str,
                     availabilities: list, day: CalendarDay, bookings: list):
        """«include» Check availability: rules 2, 4 and 1 in this order.
        Returns (available, reason, conflicting booking or None).
        """
        # Rule 2: valid time range
        if parse_time(start_time) >= parse_time(end_time):
            return False, "start_time must be before end_time", None
        # Rule 4: holiday and opening hours of this weekday
        if day.is_holiday:
            return False, f"{date} is a holiday - no bookings allowed", None
        opening = [a for a in availabilities
                   if a.room_id == self.room_id and a.weekday == day.weekday]
        if not any(a.covers(start_time, end_time) for a in opening):
            return False, "outside the room's opening hours on this weekday", None
        # Rule 1: no overlap with an active booking of this room
        requested = Booking("NEW", "", self.room_id, date, start_time, end_time)
        for booking in bookings:
            if requested.overlaps(booking):
                return (False,
                        f"room is already booked from {booking.start_time} to {booking.end_time}",
                        booking)
        return True, "room is free", None


class Student:
    def __init__(self, student_id: str, first_name: str, last_name: str, email: str,
                 street: str, street_no: str | None, postal_code: str, city: str):
        # self refers to this particular student object.
        self.student_id = student_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.street = street
        self.street_no = street_no            # optional [0..1]
        self.postal_code = postal_code
        self.city = city

    def book(self, room: Room, booking_id: str, date: str, start_time: str,
             end_time: str, event_name: str | None = None, participants: int = 1) -> Booking:
        """UML operation book(room, date, start, end): Booking.
        Creates the relationship; the caller checks the rules before and saves it after.
        """
        return Booking(booking_id, self.student_id, room.room_id, date, start_time, end_time,
                       event_name, participants, ACTIVE,
                       datetime.now().isoformat(timespec="seconds"))
