print("--- Script Starting ---")
try:
    from app.database import SessionLocal
    from app.models import User
    print("Imports successful")

    db = SessionLocal()
    email = "tonym415@gmail.com"
    print(f"Querying for {email}")

    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"User found: {user.email}")
        print(f"Role: {user.role}")
    else:
        print(f"User {email} not found.")
    db.close()
except Exception as e:
    print(f"Error occurred: {e}")
print("--- Script Finished ---")
