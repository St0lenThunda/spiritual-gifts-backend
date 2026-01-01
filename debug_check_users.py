import sys
import os

# Add the current directory to the python path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import User, Organization

def check_users():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.email.in_(["tonym415@gmail.com", "test@test.com"])).all()
        print(f"Found {len(users)} users.")
        
        for user in users:
            print(f"User: {user.email} (ID: {user.id})")
            print(f"  Org ID: {user.org_id}")
            print(f"  Role: {user.role}")
            print(f"  Status: {user.membership_status}")
            
            if user.org_id:
                org = db.query(Organization).filter(Organization.id == user.org_id).first()
                if org:
                    print(f"  Organization: {org.name} (Slug: {org.slug}, ID: {org.id})")
                    print(f"  Plan: {org.plan}")
                    print(f"  Stripe Customer ID: {org.stripe_customer_id}")
                else:
                    print(f"  Organization: <Not Found> (ID: {user.org_id})")
            else:
                print("  Organization: None")
            print("-" * 30)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
