"""FHNW Room Booking API. Start with: python run.py, then open /docs.
Built on the pattern of the School IS API reference (Student / Course / Enrolment):
here Student / Room / Booking. All records are fictional.
"""

# 1. Imports and setup: FastAPI connects HTTP requests to Python functions.
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from domain import Availability, Booking, CalendarDay, Room, Student, parse_date, parse_time
from storage import find_record, load_records, save_records

app = FastAPI(title="FHNW Room Booking API",
              description="Building / Room / Student / Booking - students book rooms for a time slot")


@app.get("/")
def welcome():
    return {"message": "FHNW Room Booking API", "documentation": "/docs"}


# 2. Read all and read one: the same pattern for every entity of our ER model.
@app.get("/buildings")
def list_buildings():
    return load_records("buildings.json")


@app.get("/buildings/{building_id}")
def get_building(building_id: str):
    for building in load_records("buildings.json"):
        if building["building_id"] == building_id:
            return building
    # Outside the loop: only report absence after inspecting all records.
    raise HTTPException(status_code=404, detail="Building not found")


@app.get("/rooms")
def list_rooms():
    return load_records("rooms.json")


@app.get("/rooms/{room_id}")
def get_room(room_id: str):
    rooms = load_records("rooms.json")                 # Load
    for room in rooms:                                 # Search
        if room["room_id"] == room_id:
            return room                                # Return
    raise HTTPException(status_code=404, detail="Room not found")


@app.get("/students")
def list_students():
    return load_records("students.json")


@app.get("/students/{student_id}")
def get_student(student_id: str):
    for student in load_records("students.json"):
        if student["student_id"] == student_id:
            return student
    raise HTTPException(status_code=404, detail="Student not found")


@app.get("/bookings")
def list_bookings():
    return load_records("bookings.json")


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: str):
    for booking in load_records("bookings.json"):
        if booking["booking_id"] == booking_id:
            return booking
    raise HTTPException(status_code=404, detail="Booking not found")


# 3. Relationships: follow the foreign keys of our model.
@app.get("/buildings/{building_id}/rooms")
def rooms_of_building(building_id: str):
    """Which rooms exist in building X, and what are their capacities? (Building 1 - 0..* Room)"""
    get_building(building_id)                          # 404 if the building does not exist
    return [room for room in load_records("rooms.json") if room["building_id"] == building_id]


@app.get("/students/{student_id}/bookings")
def bookings_of_student(student_id: str):
    """Use case 'View my bookings': active bookings of student Y (Student 1 - 0..* Booking)."""
    get_student(student_id)
    return [b for b in load_records("bookings.json")
            if b["student_id"] == student_id and b["status"] == "ACTIVE"]


@app.get("/rooms/{room_id}/bookings")
def bookings_of_room(room_id: str, date: str | None = None):
    """Who booked room X, and when? (Room 1 - 0..* Booking), optionally for one date."""
    get_room(room_id)
    result = [b for b in load_records("bookings.json")
              if b["room_id"] == room_id and b["status"] == "ACTIVE"]
    if date is not None:
        result = [b for b in result if b["date"] == date]
    return result


# 4. Business rules: the routes load records, the domain classes decide.
def check_formats(date: str, start_time: str, end_time: str):
    """'2026-02-30' or '25:00' look like a date/time but are not real ones -> 422."""
    try:
        parse_date(date)
        parse_time(start_time)
        parse_time(end_time)
    except ValueError:
        raise HTTPException(status_code=422,
                            detail="date must be YYYY-MM-DD and times HH:MM (00:00-23:59)")


def check_room(room: Room, date: str, start_time: str, end_time: str):
    """Load what the rule needs and call Room.is_available() from our class diagram."""
    availabilities = [Availability(**r) for r in load_records("availability.json")]
    bookings = [Booking(**r) for r in load_records("bookings.json")]
    day = CalendarDay.for_date(date, load_records("calendar_days.json"))
    return room.is_available(date, start_time, end_time, availabilities, day, bookings)


@app.get("/rooms/{room_id}/availability")
def check_availability(room_id: str, date: str, start_time: str, end_time: str):
    """Use case 'Find free rooms'.
    Try: /rooms/R-421/availability?date=2026-10-14&start_time=12:00&end_time=14:00
    """
    check_formats(date, start_time, end_time)
    room = Room(**get_room(room_id))
    available, reason, conflict = check_room(room, date, start_time, end_time)
    return {"room_id": room_id, "date": date, "start_time": start_time, "end_time": end_time,
            "available": available, "reason": reason,
            "conflicting_booking_id": conflict.booking_id if conflict else None}


# 5. Create: the use case 'Book a room' (Check -> Create -> Save, like registration_demo.py).
class BookingRequest(BaseModel):
    """Request body. FastAPI checks required fields and types -> 422 if they do not match."""
    student_id: str = Field(examples=["S-100234"])
    room_id: str = Field(examples=["R-421"])
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["2026-10-14"])
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$", examples=["12:00"])
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$", examples=["14:00"])
    event_name: str | None = Field(default=None, examples=["Gruppenarbeit Information Systems"])
    participants: int = Field(ge=1, examples=[3])


def next_booking_id(records):
    """B-17, B-18 ... -> the next free number."""
    numbers = [int(r["booking_id"].split("-")[1]) for r in records]
    return f"B-{max(numbers, default=0) + 1}"


@app.post("/bookings", status_code=201)
def create_booking(request: BookingRequest):
    # 5a. Check: real date and times (422), related records exist (404)
    check_formats(request.date, request.start_time, request.end_time)
    student = Student(**get_student(request.student_id))
    room = Room(**get_room(request.room_id))

    # 5b. Check: business rules (400 / 409)
    if request.participants > room.capacity:
        raise HTTPException(status_code=400,
                            detail=f"{request.participants} participants exceed the capacity of {room.capacity}")
    available, reason, conflict = check_room(room, request.date, request.start_time, request.end_time)
    if conflict is not None:
        raise HTTPException(status_code=409, detail={
            "error": "ROOM_ALREADY_BOOKED", "message": reason,
            "conflicting_booking_id": conflict.booking_id})
    if not available:
        raise HTTPException(status_code=400, detail=reason)

    # 5c. Create: call the modelled operation Student.book() - nothing saved yet
    records = load_records("bookings.json")
    booking = student.book(room, next_booking_id(records), request.date, request.start_time,
                           request.end_time, request.event_name, request.participants)

    # 5d. Save: append the record and write bookings.json
    records.append(booking.to_record())
    save_records("bookings.json", records)
    return booking.to_record()


# 6. Update: the use case 'Cancel booking' (soft cancellation, no DELETE).
@app.patch("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str):
    records = load_records("bookings.json")
    for index, record in enumerate(records):
        if record["booking_id"] == booking_id:
            booking = Booking(**record)
            if not booking.is_active():
                raise HTTPException(status_code=409, detail="Booking is already cancelled")
            booking.cancel()
            records[index] = booking.to_record()
            save_records("bookings.json", records)
            return booking.to_record()
    raise HTTPException(status_code=404, detail="Booking not found")

# Try in /docs: GET /rooms/R-421, /rooms/R-999 (404); POST /bookings with the example body (201),
# then the same request again (409); PATCH /bookings/B-17/cancel (200).
