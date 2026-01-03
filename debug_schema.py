from sqlalchemy import text
from app.database import engine

def debug_schema():
    print("Inspecting audit_logs schema...")
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(audit_logs);")).fetchall()
        for row in result:
            print(row)

if __name__ == "__main__":
    debug_schema()
