import sys
import os
from sqlalchemy import text

# Add the current directory to the python path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import User, Organization

def migrate_user():
    db = SessionLocal()
    try:
        # Target details
        user_email = "test@test.com"
        target_org_slug = "neon-ministry"
        
        # Get User
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"User {user_email} not found.")
            return

        # Get Target Org
        target_org = db.query(Organization).filter(Organization.slug == target_org_slug).first()
        if not target_org:
            print(f"Target organization {target_org_slug} not found.")
            return

        print(f"Moving user {user.email} from Org ID {user.org_id} to {target_org.name} ({target_org.id})")

        # Update
        user.org_id = target_org.id
        # Ensure status is pending as per join flow usually, or active?
        # User said "move test@test.com to neon-ministry"
        # Admin usually needs to approve, so let's keep it 'pending' if it was pending, or set to pending if we want them to be reviewed.
        # But if they were already pending in the other one, let's keep them pending here.
        
        db.commit()
        print("Migration successful.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_user()
