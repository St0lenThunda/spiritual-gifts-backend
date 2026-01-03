from sqlalchemy import text
from app.database import engine

def migrate():
    print("Migrating audit_logs table...")
    with engine.connect() as conn:
        try:
            # Attempt to add details column
            # Note: SQLite naming for JSON column is flexible, usually just ADD COLUMN details JSON works or TEXT
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN details JSON;"))
            conn.commit()
            print("Successfully added details column.")
        except Exception as e:
            print(f"Migration error (column might already exist): {e}")

if __name__ == "__main__":
    migrate()
