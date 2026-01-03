from app.database import SessionLocal
from app.models import User
import sys

db = SessionLocal()
email = "tonym415@gmail.com"

print(f"Assigning 'super_admin' role to {email}...")

try:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Try case-insensitive search if exact match fails
        user = db.query(User).filter(User.email.ilike(email)).first()

    if user:
        print(f"Found user: {user.email} (ID: {user.id})")
        print(f"Current Role: {user.role}")
        
        user.role = "super_admin"
        db.commit()
        print(f"Updated Role to: {user.role}")
    else:
        print(f"User {email} NOT FOUND in database.")
        
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
