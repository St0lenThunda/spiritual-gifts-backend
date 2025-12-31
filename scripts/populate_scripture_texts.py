import sys
import json
from pathlib import Path
from sqlalchemy import text

# Add project root to PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.database import SessionLocal
from app.models import ScriptureSet

def normalize_ref(ref):
    """Normalize reference for matching across datasets."""
    # Remove dots and spaces
    ref = ref.replace(".", "").replace(" ", "").lower()
    # Handle common abbreviations
    replacements = {
        "peter": "pet",
        "corinthians": "cor",
        "romans": "rom",
        "ephesians": "eph",
        "timothy": "tim",
        "proverbs": "prov",
        "colossians": "col",
        "matthew": "matt",
        "psalms": "ps",
        "revelation": "rev",
        "galatians": "gal",
        "philippians": "phil",
        "thessalonians": "thess",
        "hebrews": "heb"
    }
    for full, short in replacements.items():
        if full in ref:
            ref = ref.replace(full, short)
    return ref

def populate_scripture_texts():
    db = SessionLocal()
    try:
        # 1. Load the localized scripture texts from backend data folder
        # These was migrated to the backend in previous steps
        scriptures_file = Path("data/scriptures.json")
        if not scriptures_file.exists():
            print("Error: data/scriptures.json not found.")
            return

        with open(scriptures_file, "r") as f:
            bible_data = json.load(f)
            
        # Create a mapping for easier lookup
        # Map normalized ref -> full bible data entry
        bible_map = {normalize_ref(k): v for k, v in bible_data.items()}

        # 2. Get all scripture sets from DB
        scripture_sets = db.query(ScriptureSet).all()
        
        for sset in scripture_sets:
            print(f"Processing ScriptureSet: {sset.name}")
            
            # verses is a Dict[GiftName, List[VerseRefString]]
            if not sset.verses:
                continue
                
            updated_verses = {}
            for gift_name, refs in sset.verses.items():
                ref_details = []
                for ref in refs:
                    # Handle already enriched data or raw string references
                    orig_ref = ref["reference"] if isinstance(ref, dict) else ref
                    norm_ref = normalize_ref(orig_ref)
                    
                    if norm_ref in bible_map:
                        # Use the latest text from scriptures.json
                        ref_details.append(bible_map[norm_ref])
                    else:
                        # Fallback for references not in our database yet
                        # If it was already a dict, keep it as is (might have been manually added or already present)
                        if isinstance(ref, dict):
                             ref_details.append(ref)
                        else:
                            print(f"  Warning: Reference '{ref}' not found in bible data.")
                            ref_details.append({
                                "reference": ref,
                                "verses": {}
                            })
                updated_verses[gift_name] = ref_details
                
            # Assign the enriched JSON back to the column
            sset.verses = updated_verses
            db.add(sset)
            print(f"  Enriched verses for {len(updated_verses)} gifts.")
            
        db.commit()
        print("Success: All scripture sets populated with texts.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    populate_scripture_texts()
