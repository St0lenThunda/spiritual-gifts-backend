import pytest
from sqlalchemy import text
from app.database import engine

@pytest.mark.skipif("sqlite" in str(engine.url), reason="Postgres schema check skipped on SQLite")
def test_audit_logs_schema_postgres():
    print(f"Connecting to: {engine.url}")
    
    with engine.connect() as conn:
        # Check if table exists
        try:
            # Query information_schema (standard SQL)
            query = text("SELECT column_name FROM information_schema.columns WHERE table_name='audit_logs';")
            result = conn.execute(query).fetchall()
            columns = [row[0] for row in result]
            print(f"Found columns: {columns}")
            
            if not columns:
                # Fallback for SQLite in case it fails over?
                # But error was psycopg2...
                print("Table likely doesn't exist or not visible in information_schema")
                # Try SQLite pragma just in case
                try:
                    res = conn.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
                    if res:
                        print(f"SQLite Columns: {[r[1] for r in res]}")
                        columns = [r[1] for r in res]
                except:
                    pass

            assert 'details' in columns, f"'details' column missing! Columns found: {columns}"
            
        except Exception as e:
            pytest.fail(f"Schema check failed: {e}")
