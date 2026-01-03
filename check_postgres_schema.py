from sqlalchemy import text
from app.database import engine
import sys

def check_schema():
    print(f"Checking schema on: {engine.url}", file=sys.stderr)
    with engine.connect() as conn:
        try:
            result = conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='audit_logs';"
            )).fetchall()
            print("Columns in audit_logs:", file=sys.stderr)
            for row in result:
                print(f" - {row[0]} ({row[1]})", file=sys.stderr)
        except Exception as e:
            print(f"Error checking schema: {e}", file=sys.stderr)

if __name__ == "__main__":
    check_schema()
