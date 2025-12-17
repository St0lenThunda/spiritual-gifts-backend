from sqlalchemy import text
from app.database import engine

def migrate():
    print("Starting migration...")
    with engine.connect() as conn:
        # Migration 1: Add created_at column
        try:
            conn.execute(text("ALTER TABLE surveys ADD COLUMN created_at TIMESTAMP;"))
            conn.commit()
            print("Migration successful: Added created_at column.")
        except Exception as e:
            print(f"Migration 1 skipped (column may already exist): created_at")
        
        # Migration 2: Add user_id column with foreign key
        try:
            conn.execute(text("ALTER TABLE surveys ADD COLUMN user_id INTEGER REFERENCES users(id);"))
            conn.commit()
            print("Migration successful: Added user_id column.")
        except Exception as e:
            print(f"Migration 2 skipped (column may already exist): user_id")

if __name__ == "__main__":
    migrate()
