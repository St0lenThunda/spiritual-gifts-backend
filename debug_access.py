from app.database import SessionLocal
from app.models import User, Organization
from app.services.entitlements import get_org_features

db = SessionLocal()

import sys

# Redirect stdout/stderr to file
sys.stdout = open("debug_output.txt", "w")
sys.stderr = sys.stdout

print("Starting debug script...")
try:
    print(f"Connecting to DB...")
    # List all users first to see if we are in empty DB
    all_users = db.query(User).limit(5).all()
    print(f"Total Users in DB (sample 5): {[u.email for u in all_users]}")

     # ... (rest of logic same) ...
    for email in emails:
        print(f"\nChecking {email}...")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} NOT FOUND")
            # Try partial match?
            continue

        print(f"User: {email} (ID: {user.id})")
        print(f"  Role: {user.role}")
        
        if user.org_id:
            org = db.query(Organization).filter(Organization.id == user.org_id).first()
            if org:
                print(f"  Org: {org.name} (ID: {org.id})")
                print(f"  Plan: {org.subscription_plan}")
                
                # Check effective features
                features = get_org_features(org.subscription_plan)
                print(f"  Computed Features: {list(features.keys())}")
                print(f"  Has 'audit_logs'? {'audit_logs' in features}")
            else:
                print("  Org found in User but not in Org table (Data integrity issue?)")
        else:
            print("  No Organization assigned.")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
print("-" * 50)
sys.stdout.close()
