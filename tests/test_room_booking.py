"""Behaviour checks for our business rules; all writes use temporary copies of the data.
Run from the project folder:  python -m unittest discover -s tests -v
"""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
import storage  # noqa: E402
from domain import Booking, Room, Student  # noqa: E402

EXAMPLE = {"student_id": "S-100234", "room_id": "R-421", "date": "2026-10-14",
           "start_time": "12:00", "end_time": "14:00",
           "event_name": "Gruppenarbeit Information Systems", "participants": 3}


class RoomBookingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        shutil.copytree(Path(__file__).resolve().parents[1] / "data", self.data)
        self.patch = patch.object(storage, "DATA_DIR", self.data)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.data.glob("*.json")}

    def book(self, **changes):
        return self.client.post("/bookings", json={**EXAMPLE, **changes})

    # --- Read operations -------------------------------------------------
    def test_read_all_and_read_one(self):
        before = self.snapshot()
        for path, expected in [("/buildings", 2), ("/rooms", 3), ("/students", 2), ("/bookings", 1)]:
            self.assertEqual(len(self.client.get(path).json()), expected)
        self.assertEqual(self.client.get("/rooms/R-421").json()["capacity"], 8)
        self.assertEqual(len(self.client.get("/buildings/B-OLT/rooms").json()), 2)
        self.assertEqual(before, self.snapshot(), "GET must not change stored data")

    def test_unknown_ids_return_404(self):
        for path in ["/rooms/R-999", "/students/S-999999", "/bookings/B-999", "/buildings/X"]:
            self.assertEqual(self.client.get(path).status_code, 404)

    # --- Use case: Book a room -------------------------------------------
    def test_adjacent_booking_is_created(self):
        response = self.book()                      # B-17 ends 12:00, we start 12:00
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["booking_id"], "B-18")
        self.assertEqual(response.json()["status"], "ACTIVE")
        self.assertEqual(self.client.get("/bookings/B-18").json(), response.json())

    def test_overlap_is_rejected_and_nothing_saved(self):
        before = self.snapshot()
        response = self.book(start_time="11:00", end_time="13:00")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["conflicting_booking_id"], "B-17")
        self.assertEqual(before, self.snapshot())

    def test_same_request_twice(self):
        self.assertEqual(self.book().status_code, 201)
        self.assertEqual(self.book().status_code, 409)

    def test_rule_violations_return_400(self):
        cases = [dict(start_time="15:00", end_time="14:00"),       # rule 2
                 dict(start_time="21:00", end_time="22:00"),       # rule 4: opening hours
                 dict(date="2026-12-25"),                          # rule 4: holiday
                 dict(room_id="R-422", participants=6)]            # rule 5: capacity
        for case in cases:
            self.assertEqual(self.book(**case).status_code, 400, case)

    def test_unknown_references_return_404(self):
        self.assertEqual(self.book(student_id="S-999999").status_code, 404)
        self.assertEqual(self.book(room_id="R-999").status_code, 404)

    def test_invalid_input_returns_422(self):
        missing = {k: v for k, v in EXAMPLE.items() if k != "room_id"}
        self.assertEqual(self.client.post("/bookings", json=missing).status_code, 422)
        self.assertEqual(self.book(participants="drei").status_code, 422)
        self.assertEqual(self.book(end_time="25:00").status_code, 422)

    # --- Use case: Cancel booking / View my bookings ---------------------
    def test_soft_cancellation_frees_the_room(self):
        query = "/rooms/R-421/availability?date=2026-10-14&start_time=10:00&end_time=12:00"
        self.assertFalse(self.client.get(query).json()["available"])
        response = self.client.patch("/bookings/B-17/cancel")
        self.assertEqual(response.json()["status"], "CANCELLED")
        self.assertEqual(len(self.client.get("/bookings").json()), 1, "record is kept")
        self.assertTrue(self.client.get(query).json()["available"])
        self.assertEqual(self.client.patch("/bookings/B-17/cancel").status_code, 409)

    def test_view_my_bookings_shows_only_active(self):
        self.book()
        self.assertEqual(len(self.client.get("/students/S-100234/bookings").json()), 1)
        self.client.patch("/bookings/B-18/cancel")
        self.assertEqual(self.client.get("/students/S-100234/bookings").json(), [])

    # --- Domain classes without HTTP -------------------------------------
    def test_objects_do_not_implicitly_save(self):
        before = self.snapshot()
        student = Student(**storage.find_record("students.json", "student_id", "S-100234"))
        room = Room(**storage.find_record("rooms.json", "room_id", "R-421"))
        booking = student.book(room, "B-X", "2026-10-14", "12:00", "14:00")
        self.assertEqual(booking.to_record()["room_id"], "R-421")
        self.assertEqual(before, self.snapshot())

    def test_overlap_rule_is_half_open(self):
        a = Booking("B-1", "S", "R-421", "2026-10-14", "10:00", "12:00")
        self.assertFalse(a.overlaps(Booking("B-2", "S", "R-421", "2026-10-14", "12:00", "14:00")))
        self.assertTrue(a.overlaps(Booking("B-3", "S", "R-421", "2026-10-14", "11:00", "13:00")))
        self.assertFalse(a.overlaps(Booking("B-4", "S", "R-422", "2026-10-14", "11:00", "13:00")))


if __name__ == "__main__":
    unittest.main()
