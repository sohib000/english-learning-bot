import json, os
from config import LESSONS_DIR

def load_lesson(level: int, lesson_number: int) -> dict | None:
    path = os.path.join(LESSONS_DIR, f"level_{level}", f"lesson_{lesson_number:03d}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def get_total_lessons(level: int) -> int:
    path = os.path.join(LESSONS_DIR, f"level_{level}")
    if not os.path.exists(path):
        return 0
    return len([f for f in os.listdir(path) if f.endswith(".json")])
