"""JSON file access (data access layer).
Same pattern as storage.py in the School IS API reference.
"""
import json
from pathlib import Path

# Relative to this file, so starting Python in another folder still works.
DATA_DIR = Path(__file__).resolve().parent / "data"


def load_records(filename: str):
    """Read JSON text and return Python lists/dictionaries."""
    with (DATA_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


def save_records(filename: str, records):
    """Replace the file with the supplied records (used when a booking is created or cancelled)."""
    with (DATA_DIR / filename).open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)
        file.write("\n")


def find_record(filename: str, key: str, value):
    """Return the first record whose <key> equals <value>, or None after checking all records."""
    for record in load_records(filename):
        if record[key] == value:
            return record
    return None

# Filenames come from our code, never from arbitrary user input.
# JSON files do not enforce foreign keys or support concurrent transactions:
# our code checks the references (404) and assumes a single writer.
