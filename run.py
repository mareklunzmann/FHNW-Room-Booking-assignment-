"""Development launcher. Terminal command: python run.py   (or: python run.py tutorial)"""
from pathlib import Path
import sys
import uvicorn

if __name__ == "__main__":
    # Start either the room booking app or the small tutorial, one at a time.
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] != "tutorial"):
        raise SystemExit("Use: python run.py [tutorial]")
    folder = Path(__file__).resolve().parent
    module = "tutorial" if len(sys.argv) == 2 else "main"
    uvicorn.run(f"{module}:app", host="0.0.0.0", port=8000,
                reload=True, reload_dirs=[str(folder)], app_dir=str(folder))
