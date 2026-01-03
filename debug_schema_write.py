from sqlalchemy import text
from app.database import engine
import os

def check():
    output_path = "backend_schema_check.txt"
    try:
        with open(output_path, "w") as f:
            f.write("Checking schema...\n")
            with engine.connect() as conn:
                try:
                    result = conn.execute(text("PRAGMA table_info(audit_logs);")).fetchall()
                    if not result:
                        f.write("Table 'audit_logs' not found or empty info.\n")
                    for row in result:
                        f.write(f"{row}\n")
                except Exception as e:
                    f.write(f"Error executing pragma: {e}\n")
    except Exception as e:
        # Fallback if file open fails
        print(f"Failed to write file: {e}")

if __name__ == "__main__":
    check()
