import sqlite3
import pytest
import os
from sqlalchemy import create_engine, text

# Use direct path to be sure
DB_PATH = "backend/test.db"
# Fallback if running from backend dir
if not os.path.exists(DB_PATH) and os.path.exists("test.db"):
    DB_PATH = "test.db"

def test_force_migration():
    print(f"Migrating {DB_PATH}...", flush=True)
    assert os.path.exists(DB_PATH), f"DB not found at {DB_PATH}"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(audit_logs)")
    cols = cursor.fetchall()
    col_names = [c[1] for c in cols]
    print(f"Columns before: {col_names}")
    
    if 'details' not in col_names:
        print("Adding details column...")
        try:
            cursor.execute("ALTER TABLE audit_logs ADD COLUMN details JSON")
            conn.commit()
            print("Added details column.")
        except Exception as e:
            pytest.fail(f"Alter table failed: {e}")
            
    # Verify
    cursor.execute("PRAGMA table_info(audit_logs)")
    cols_after = cursor.fetchall()
    col_names_after = [c[1] for c in cols_after]
    print(f"Columns after: {col_names_after}")
    
    conn.close()
    
    assert 'details' in col_names_after
