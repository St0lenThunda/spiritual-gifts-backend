from sqlalchemy import text
from app.database import engine
import sys
import os

def migrate_real_db():
    log_file = "/home/thunda/Dev/543_Tools/spiritual-gifts/backend/pg_migration.log"
    with open(log_file, "w") as f:
        f.write(f"Connecting to DB using engine: {engine.url}...\n")
        
        try:
            with engine.connect() as conn:
                f.write("Checking for 'details' column in audit_logs...\n")
                
                # Postgres introspection
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='audit_logs' AND column_name='details';"
                )).fetchall()
                
                if not result:
                    f.write("Adding 'details' column...\n")
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN details JSONB;"))
                    conn.commit()
                    f.write("Migration successful.\n")
                else:
                    f.write("'details' column already exists.\n")
                    
        except Exception as e:
            f.write(f"Migration error: {e}\n")

if __name__ == "__main__":
    migrate_real_db()
