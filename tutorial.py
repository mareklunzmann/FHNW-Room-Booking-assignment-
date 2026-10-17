"""Small FastAPI example. Start with: python run.py tutorial
Stop the other app first (Ctrl+C); both use port 8000.
Adapted from the School IS API tutorial.py and the FastAPI First Steps / Path Parameters tutorials.
"""
from fastapi import FastAPI

app = FastAPI(title="First room booking API")


@app.get("/")
def welcome():
    return {"message": "Hello from the room booking API"}


@app.get("/rooms/{room_id}")
def show_input(room_id: str):
    # Only echoes the input: this tutorial does not look up a stored room.
    return {"requested_room_id": room_id}
