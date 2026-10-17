"""Restore the starting bookings after trying POST / PATCH in /docs.
Run: python reset_data.py
"""
import shutil
from pathlib import Path

data = Path(__file__).resolve().parent / "data"
shutil.copyfile(data / "bookings.initial.json", data / "bookings.json")
print("data/bookings.json restored: only booking B-17 (R-421, 2026-10-14, 10:00-12:00)")
