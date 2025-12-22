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
    
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.email == 'tonym415@gmail.com').first()
            if user:
                print(f"SUCCESS: Found user {user.email} with role '{user.role}'")
            else:
                print("ERROR: User not found")
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    verify()
