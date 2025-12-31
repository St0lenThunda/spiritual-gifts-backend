import sys
import json
from pathlib import Path

# Add project root to PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.database import SessionLocal
from app.models import ScriptureSet

def verify_scripture_data():
    db = SessionLocal()
    try:
        scripture_sets = db.query(ScriptureSet).all()
        print(f"Checking {len(scripture_sets)} scripture sets...\n")
        
        required_versions = ["KJV", "NIV", "ESV", "RVR1960", "LSG", "SYNOD"]
        
        all_passed = True
        for sset in scripture_sets:
            print(f"Set: {sset.name}")
            if not sset.verses:
                print("  [SKIP] No verses defined.")
                continue
            
            missing_versions_in_set = set()
            total_refs = 0
            enriched_refs = 0
            
            for gift_name, refs in sset.verses.items():
                for ref_obj in refs:
                    total_refs += 1
                    if not isinstance(ref_obj, dict):
                        print(f"  [FAIL] Reference in gift '{gift_name}' is not an object: {ref_obj}")
                        all_passed = False
                        continue
                    
                    enriched_refs += 1
                    versions = ref_obj.get("verses", {})
                    for v in required_versions:
                        if v not in versions or not versions[v]:
                            missing_versions_in_set.add(v)
            
            print(f"  Refs: {enriched_refs}/{total_refs} enriched.")
            if missing_versions_in_set:
                print(f"  [WARN] Missing versions across some refs: {', '.join(sorted(missing_versions_in_set))}")
            else:
                print("  [PASS] All core versions present in all enriched refs.")
            print("-" * 20)

        if all_passed:
            print("\nVerification Complete: Data structure is correct.")
        else:
            print("\nVerification Failed: Found structural issues.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_scripture_data()
