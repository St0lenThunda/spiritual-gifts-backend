from app.database import engine
from sqlalchemy import text
import sys

def migrate():
    print(f"Dialect: {engine.dialect.name}")
    
    # Determine column type syntax
    col_type = "JSON"
    if engine.dialect.name == "sqlite":
        # SQLite doesn't strictly enforce JSON type, TEXT/JSON allows generic storage
        col_type = "JSON" 
    elif engine.dialect.name == "postgresql":
        col_type = "JSONB"  # Prefer JSONB for Postgres
        
    sql = text(f"ALTER TABLE organizations ADD COLUMN branding {col_type}")
    
    try:
        with engine.connect() as conn:
            conn.execute(sql)
            conn.commit()
            print("Successfully added 'branding' column.")
    except Exception as e:
        if "duplicate column" in str(e) or "no such table" in str(e):
            print(f"Migration skipped or failed: {e}")
        else:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    migrate()
