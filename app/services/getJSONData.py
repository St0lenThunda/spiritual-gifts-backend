import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = BASE_DIR / "data" / "questions.json"
GIFTS_FILE = BASE_DIR / "data" / "gifts.json"   
SCRIPTURES_FILE = BASE_DIR / "data" / "scriptures.json"

def load_questions():
    with QUESTIONS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)
def load_gifts():
    with GIFTS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)
def load_scriptures():
    with SCRIPTURES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

if __name__ == "__main__":
    print(load_questions())