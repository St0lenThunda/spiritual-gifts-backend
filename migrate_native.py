import sqlite3
import sys
import os

db_path = "test.db"
log_path = "migration_log.txt"

def log(msg):
    with open(log_path, "a") as f:
        f.write(msg + "\n")

def migrate():
    # Clear log
    if os.path.exists(log_path):
        os.remove(log_path)
        
    log(f"Opening {db_path}...")
    try:
        if not os.path.exists(db_path):
            log(f"Error: DB file {db_path} does not exist!")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table info
        try:
            cursor.execute("PRAGMA table_info(audit_logs)")
            cols = cursor.fetchall()
            log(f"Current columns: {[c[1] for c in cols]}")
            
            has_details = any(c[1] == 'details' for c in cols)
            
            if not has_details:
                log("Adding 'details' column...")
                try:
                    cursor.execute("ALTER TABLE audit_logs ADD COLUMN details JSON")
                    conn.commit()
                    log("Migration successful.")
                except Exception as e:
                    log(f"Error adding column: {e}")
            else:
                log("'details' column already exists.")
        except Exception as e:
            log(f"Error reading table info: {e}")
            
        conn.close()
    except Exception as e:
        log(f"Database error: {e}")

if __name__ == "__main__":
    migrate()
