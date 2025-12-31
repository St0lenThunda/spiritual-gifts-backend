
import sys
from pathlib import Path

# Add project root to PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.database import SessionLocal
from app.models import Denomination

db = SessionLocal()
try:
    denoms = db.query(Denomination).all()
    print(f"Total denominations found: {len(denoms)}")
    for d in denoms:
        print(f" - {d.slug}: {d.display_name}")
finally:
    db.close()
