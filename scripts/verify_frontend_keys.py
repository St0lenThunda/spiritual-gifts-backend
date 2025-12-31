import json
from pathlib import Path

def verify_frontend_keys():
    locales = ["en", "es", "fr", "ru"]
    base_path = Path("/home/thunda/Dev/543_Tools/spiritual-gifts/frontend/src/locales")
    
    canonical_keys = {
        "ADMINISTRATION", "APOSTLESHIP", "DISCERNMENT", "ENCOURAGEMENT",
        "EVANGELISM", "FAITH", "GIVING", "HEALING", "HELPS", "HOSPITALITY",
        "INTERCESSION", "KNOWLEDGE", "LEADERSHIP", "MERCY", "MIRACLES",
        "PROPHECY", "SERVICE", "SHEPHERD", "TEACHING", "TONGUES",
        "INTERPRETATION", "WISDOM"
    }
    
    perfect = True
    for loc in locales:
        file_path = base_path / f"{loc}.json"
        with open(file_path, 'r') as f:
            data = json.load(f)
            gift_list = data.get("gifts", {}).get("list", {})
            present_keys = set(gift_list.keys())
            
            missing = canonical_keys - present_keys
            extra = present_keys - canonical_keys
            
            print(f"Locale {loc}: {len(present_keys)} keys")
            if missing:
                print(f"  MISSING: {missing}")
                perfect = False
            if extra:
                print(f"  EXTRA: {extra}")
                perfect = False

    if perfect:
        print("\nSUCCESS: All frontend locale files are perfectly reconciled!")
    else:
        print("\nFAILURE: Key mismatch detected in frontend locales.")

if __name__ == "__main__":
    verify_frontend_keys()
