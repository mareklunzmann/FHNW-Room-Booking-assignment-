# FHNW Room Booking API

**Information Systems (MSc BIS, FHNW, HS26) – Milestone 3 prototype.**
Students reserve a room for a time slot, and anyone can see which rooms are free or booked.
The code follows the structure of the lecture's [School IS API](https://github.com/DevidMontecchiari/School-IS-api) reference: *Student / Course / Enrolment* becomes *Student / Room / Booking*. All records are fictional.

## Group members and contributions

| Member | Contributions |
| --- | --- |
| Mark [surname] | [e.g. ER model and business rules, UML class diagram, API implementation, testing, report chapters 4–5] |
| Cedric [surname] | [e.g. scope and use cases, JSON examples, Swagger tests and screenshots, report chapters 1–3] |

## 1. Install the dependencies

### Option A: GitHub Codespaces (no installation on your computer)

1. On GitHub choose **Code → Codespaces → Create codespace on main**.
2. Wait until the setup has finished. It installs the dependencies automatically (`.devcontainer/devcontainer.json`).

### Option B: Your own computer (Python 3.12 or newer)

```sh
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt` contains the two direct dependencies: **FastAPI** (web framework) and **Uvicorn** (server).

## 2. Start the API

```sh
python run.py
```

The terminal shows `Uvicorn running on http://0.0.0.0:8000`. Keep it running; **Ctrl+C** stops the API.

- Codespaces: **Ports → 8000 → Open in Browser**, then append `/docs` to the address.
- Own computer: open <http://127.0.0.1:8000/docs>.

## 3. Reproduce the example request and JSON result

Starting data: booking **B-17** already occupies room **R-421** on 14 October 2026 from 10:00 to 12:00.
If you have tested before, first restore this state with `python reset_data.py`.

In `/docs` open **POST /bookings → Try it out**, paste this body and click **Execute**:

```json
{
  "student_id": "S-100234",
  "room_id": "R-421",
  "date": "2026-10-14",
  "start_time": "12:00",
  "end_time": "14:00",
  "event_name": "Gruppenarbeit Information Systems",
  "participants": 3
}
```

Alternatively in a second terminal:

```sh
curl -X POST http://127.0.0.1:8000/bookings -H "Content-Type: application/json" \
  -d '{"student_id":"S-100234","room_id":"R-421","date":"2026-10-14","start_time":"12:00","end_time":"14:00","event_name":"Gruppenarbeit Information Systems","participants":3}'
```

Expected result: **201 Created**

```json
{
  "booking_id": "B-18",
  "student_id": "S-100234",
  "room_id": "R-421",
  "date": "2026-10-14",
  "start_time": "12:00",
  "end_time": "14:00",
  "event_name": "Gruppenarbeit Information Systems",
  "participants": 3,
  "status": "ACTIVE",
  "created_at": "<time of your request>"
}
```

The slot starts exactly when B-17 ends, which is allowed (half-open time slots). Sending the same request a second time returns **409 Conflict**, because B-18 now occupies the slot. Run `python reset_data.py` afterwards.

## 4. Automated checks (optional)

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

12 tests cover reading, the four business rules, adjacent vs. overlapping bookings, cancellation and invalid input. They work on temporary copies, so `data/` is not changed.

## Files

```text
main.py                 HTTP routes (presentation layer)
domain.py               classes from our UML class diagram + business rules (domain logic)
storage.py              load and save JSON files (data access)
data/                   fictional buildings, rooms, students, availability, calendar days, bookings
tutorial.py             minimal FastAPI example: python run.py tutorial
objects_demo.py         UML operation -> object -> JSON, without saving: python objects_demo.py
reset_data.py           restore data/bookings.json from bookings.initial.json
run.py                  starts the development server
tests/                  automated behaviour checks
.devcontainer/          Codespaces setup
```

## Endpoints

| Method | Path | Use case / question | CRUD |
| --- | --- | --- | --- |
| GET | `/buildings`, `/buildings/{building_id}` | Which buildings exist? | Read |
| GET | `/buildings/{building_id}/rooms` | Which rooms are in building X, with which capacity? | Read |
| GET | `/rooms`, `/rooms/{room_id}` | Show rooms | Read |
| GET | `/rooms/{room_id}/availability?date=&start_time=&end_time=` | Find free rooms | Read |
| GET | `/rooms/{room_id}/bookings?date=` | Who booked room X, and when? | Read |
| GET | `/students`, `/students/{student_id}` | Show students | Read |
| GET | `/students/{student_id}/bookings` | View my bookings (active only) | Read |
| GET | `/bookings`, `/bookings/{booking_id}` | Show bookings | Read |
| POST | `/bookings` | Book a room («include» Check availability) | Create |
| PATCH | `/bookings/{booking_id}/cancel` | Cancel booking (soft cancellation) | Update |

## Business rules and status codes

| Rule | Where in the code | Response if violated |
| --- | --- | --- |
| Required fields and types | `BookingRequest`, `check_formats()` | 422 |
| Student and room must exist | `get_student()`, `get_room()` | 404 |
| 1 No overlap with an active booking (half-open) | `Booking.overlaps()` | 409 |
| 2 Start before end | `Room.is_available()` | 400 |
| 3 Soft cancellation | `Booking.cancel()` | 409 if already cancelled |
| 4 Opening hours and holidays | `Availability.covers()`, `CalendarDay` | 400 |
| 5 Participants ≤ capacity (proposal) | `create_booking()` | 400 |

## Boundaries

No login or authorisation: a `student_id` selects a record but does not prove identity. JSON files are teaching storage without transactions, so the overlap check is only reliable with one writer at a time. `calendar_days.json` lists special days only; other dates count as normal days with a derived weekday. Opening hours are the same every week.
