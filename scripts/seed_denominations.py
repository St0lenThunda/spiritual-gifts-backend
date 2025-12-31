#!/usr/bin/env python3
"""Seed default denomination and scripture set for multi‑denominational support.
Run with: python scripts/seed_denominations.py
"""
import sys
import uuid
from pathlib import Path

# Add project root to PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.database import SessionLocal, engine, Base
from app.models import Denomination, ScriptureSet
from sqlalchemy.orm import sessionmaker

def main():
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        denominations_data = [
            {
                "slug": "spiritual_gifts",
                "display_name": "Spiritual Gifts",
                "scripture_set_name": "Spiritual Gifts Core",
                "verses": {} # Default uses gifts.json
            },
            {
                "slug": "catholic",
                "display_name": "Catholic Church",
                "scripture_set_name": "Catholic Lectionary",
                "verses": {
                    "Administration": ["1 Cor. 12:28", "Luke 14:28"],
                    "Shepherd": ["John 21:15-17", "1 Peter 5:2-3"],
                    "Service": ["1 Peter 4:10-11", "Matt. 20:25-28"],
                    "Giving": ["2 Cor. 9:7", "Luke 6:38"]
                }
            },
            {
                "slug": "baptist",
                "display_name": "Baptist Convention",
                "scripture_set_name": "Baptist Standard",
                "verses": {
                    "Prophecy": ["Rom. 12:6", "2 Tim. 4:2"], # Emphasis on Preaching
                    "Teaching": ["2 Tim. 2:15", "James 3:1"],
                    "Evangelism": ["Matt. 28:19-20", "Rom. 10:14-15"],
                    "Knowledge": ["Prov. 2:6", "Col. 2:2-3"]
                }
            },
            {
                "slug": "pentecostal",
                "display_name": "Pentecostal / Charismatic",
                "scripture_set_name": "Charismatic Emphasis",
                "verses": {
                    "Tongues": ["Acts 2:4", "1 Cor. 14:2", "Jude 20"],
                    "Miracles": ["Mark 16:17-18", "Acts 4:30"],
                    "Healing": ["James 5:14-15", "Acts 3:6"],
                    "Prophecy": ["Acts 2:17", "1 Cor. 14:3", "1 Cor. 14:31"]
                }
            }
        ]

        for denom_data in denominations_data:
            # 1. UPSERT Scripture Set
            ss = db.query(ScriptureSet).filter(ScriptureSet.name == denom_data["scripture_set_name"]).first()
            if not ss:
                ss = ScriptureSet(
                    name=denom_data["scripture_set_name"],
                    verses=denom_data["verses"]
                )
                db.add(ss)
                db.flush()
                print(f"Created ScriptureSet: {ss.name}")
            else:
                ss.verses = denom_data["verses"]
                db.add(ss)
                db.flush()
                print(f"Updated ScriptureSet: {ss.name}")
            
            # 2. UPSERT Denomination
            existing = db.query(Denomination).filter(Denomination.slug == denom_data["slug"]).first()
            if existing:
                existing.scripture_set_id = ss.id
                existing.display_name = denom_data["display_name"]
                # existing.scripture_set updated via relation typically, but setting ID is safer here
                print(f"Updated denomination: {denom_data['display_name']}")
            else:
                denom = Denomination(
                    slug=denom_data["slug"],
                    display_name=denom_data["display_name"],
                    logo_url=None,
                    default_currency="USD",
                    scripture_set_id=ss.id
                )
                db.add(denom)
                print(f"Created denomination: {denom_data['display_name']}")
            
            db.commit()

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
