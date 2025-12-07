import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = BASE_DIR / "data" / "questions.json"

def load_questions():
    with QUESTIONS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)
