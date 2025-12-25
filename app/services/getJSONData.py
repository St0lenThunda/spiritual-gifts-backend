import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOCALES_DIR = DATA_DIR / "locales"

def load_questions(locale: str = "en"):
    file_path = LOCALES_DIR / f"questions_{locale}.json"
    if not file_path.exists():
        file_path = DATA_DIR / "questions.json"
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_gifts(locale: str = "en"):
    file_path = LOCALES_DIR / f"gifts_{locale}.json"
    if not file_path.exists():
        file_path = DATA_DIR / "gifts.json"
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_scriptures():
    scriptures_file = DATA_DIR / "scriptures.json"
    with scriptures_file.open("r", encoding="utf-8") as f:
        return json.load(f)
