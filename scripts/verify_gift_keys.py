import json
from pathlib import Path

def verify_keys():
    locales_dir = Path("data/locales")
    gift_files = list(locales_dir.glob("gifts_*.json"))
    
    all_keys = {}
    for f in gift_files:
        with open(f, 'r') as j:
            data = json.load(j)
            all_keys[f.name] = set(data.keys())
            print(f"{f.name}: {len(data.keys())} keys")

    base_file = "gifts_en.json"
    base_keys = all_keys[base_file]
    
    perfect = True
    for fname, keys in all_keys.items():
        if fname == base_file: continue
        
        missing = base_keys - keys
        extra = keys - base_keys
        
        if missing:
            print(f"File {fname} is MISSING keys: {missing}")
            perfect = False
        if extra:
            print(f"File {fname} has EXTRA keys: {extra}")
            perfect = False
            
    if perfect:
        print("\nSUCCESS: All gift locale files are perfectly reconciled!")
    else:
        print("\nFAILURE: Key mismatch detected.")

if __name__ == "__main__":
    verify_keys()
