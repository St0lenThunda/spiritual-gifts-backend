import os
from app.database import SessionLocal
from app.models import User

def assign():
    db = SessionLocal()
    email = "tonym415@gmail.com"
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = db.query(User).filter(User.email.ilike(email)).first()
        
        if user:
            print(f"Assigning super_admin to {user.email}")
            user.role = "super_admin"
            db.commit()
            print("Commit successful")
        else:
            print(f"User {email} not found")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    assign()
