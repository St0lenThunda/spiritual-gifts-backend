import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from app.models import User
from app.config import settings

def verify():
    print(f"Connecting to: {settings.DATABASE_URL[:20]}...")
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == 'tonym415@gmail.com').first()
        if user:
            print(f"SUCCESS: Found user {user.email} with role '{user.role}'")
        else:
            print("ERROR: User not found")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
