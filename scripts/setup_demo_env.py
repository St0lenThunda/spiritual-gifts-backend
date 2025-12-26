#!/usr/bin/env python3
"""
Setup script for Demo Environment and User Migration.
1. Creates "Grace Community Fellowship" as a read-only Demo Org.
2. Creates "Neon Evangelion Ministry" for specific stakeholders.
3. Migrates any users without an organization to the Demo Org.
"""

import sys
import os
import random
from datetime import datetime

# Add parent directory to path
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Base, Organization, User
from app.services.entitlements import Plan
from app.models import Survey

def setup_demo_env():
    db = SessionLocal()
    try:
        print("🚀 Starting Demo Environment Setup...")
        
        # 1. Create/Update Demo Org
        demo_org = db.query(Organization).filter(Organization.slug == "grace-community").first()
        if not demo_org:
            print("Creating Demo Org: Grace Community Fellowship...")
            demo_org = Organization(
                name="Grace Community Fellowship",
                slug="grace-community",
                plan=Plan.CHURCH,
                is_demo=True,
                branding={"theme_preset": "theme-light", "primary_color": "#0f172a"}
            )
            db.add(demo_org)
        else:
            print("Updating Demo Org: Grace Community Fellowship...")
            demo_org.is_demo = True
            demo_org.plan = Plan.CHURCH
        
        db.commit()
        db.refresh(demo_org)
        print(f"✅ Demo Org Ready: {demo_org.id}")

        # 2. Create/Update Neon Evangelion Ministry
        neon_org = db.query(Organization).filter(Organization.slug == "neon-evangelion").first()
        if not neon_org:
            print("Creating Neon Evangelion Ministry...")
            neon_org = Organization(
                name="Neon Evangelion Ministry",
                slug="neon-evangelion",
                plan=Plan.CHURCH,  # Assuming high tier for internal use
                is_demo=False,
                branding={"theme_preset": "theme-synthwave", "primary_color": "#ff00ff"}
            )
            db.add(neon_org)
            db.commit()
            db.refresh(neon_org)
            print(f"✅ Neon Evangelion Org Ready: {neon_org.id}")
        else:
             print(f"✅ Neon Evangelion Org Exists: {neon_org.id}")

        # 3. Migrate Users
        print("\n🔍 Scanning for floating users...")
        floating_users = db.query(User).filter(User.org_id == None).all()
        
        migrated_count = 0
        for user in floating_users:
            if user.email == "tonym415@gmail.com":
                print(f"  👉 Moving {user.email} to Neon Evangelion...")
                user.org_id = neon_org.id
                user.role = "admin" # Ensure admin
            else:
                print(f"  👉 Moving {user.email} to Demo Org...")
                user.org_id = demo_org.id
                user.role = "user" # Default to user role in demo?
            
            migrated_count += 1
        
        if migrated_count > 0:
            db.commit()
            print(f"✅ Migrated {migrated_count} users.")
        else:
            print("✅ No floating users found.")

        # 4. Ensure Seed Users Exist
        seed_users = [
            {"email": "super@neon.com", "role": "admin", "org_id": neon_org.id, "desc": "Super Admin"},
            {"email": "admin@grace.com", "role": "admin", "org_id": demo_org.id, "desc": "Demo Org Admin"},
            {"email": "user@grace.com", "role": "user", "org_id": demo_org.id, "desc": "Demo Org Member"},
        ]
        
        print("\n🌱 Seeding Test Users...")
        for seed in seed_users:
            u = db.query(User).filter(User.email == seed["email"]).first()
            if not u:
                u = User(
                    email=seed["email"],
                    role=seed["role"],
                    org_id=seed["org_id"],
                    created_at=datetime.utcnow()
                )
                db.add(u)
                print(f"  ✅ Created {seed['desc']}: {seed['email']}")
            else:
                # Ensure correct state
                u.role = seed["role"]
                u.org_id = seed["org_id"]
                print(f"  ✅ Verified {seed['desc']}: {seed['email']}")
        
        db.commit()
        # Generate sample assessments for each seeded user
        from random import randint
        for seed in seed_users:
            # Retrieve the user record (ensure we have the latest DB object)
            user_obj = db.query(User).filter(User.email == seed["email"]).first()
            if not user_obj:
                continue
            # Create between 1 and 5 assessments
            for _ in range(randint(1, 5)):
                assessment = Survey(
                    user_id=user_obj.id,
                    org_id=user_obj.org_id,
                    answers={"question_1": "answer_a", "question_2": "answer_b"},
                    scores={"overall": randint(50, 100)},
                    assessment_version="1.0",
                    created_at=datetime.utcnow()
                )
                db.add(assessment)
        db.commit()

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_demo_env()
