import json
from app.database import SessionLocal
from app.models import ScriptureSet

def populate_scriptures():
    db = SessionLocal()
    try:
        # Load base gifts to extract core references
        with open('data/locales/gifts_en.json', 'r') as f:
            gifts = json.load(f)
        
        core_verses = {}
        for gift_name, data in gifts.items():
            core_verses[gift_name] = data.get('scriptures', [])
            
        # Update 'Spiritual Gifts Core' set
        core_set = db.query(ScriptureSet).filter_by(name='Spiritual Gifts Core').first()
        if core_set:
            core_set.verses = core_verses
            print(f"Updated 'Spiritual Gifts Core' with {len(core_verses)} entries.")
        else:
            print("Error: 'Spiritual Gifts Core' set not found.")
            
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_scriptures()
