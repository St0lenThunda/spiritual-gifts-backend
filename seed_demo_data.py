#!/usr/bin/env python3
"""
Seed script for demo organization data.
Creates two organizations with members and sample assessment data.

Usage:
    python -m app.seed_demo_data

Or from the backend directory:
    python seed_demo_data.py
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Add parent directory to path if running as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Base, Organization, User, Survey


# Spiritual gifts for score generation
SPIRITUAL_GIFTS = [
    "ADMINISTRATION", "APOSTLESHIP", "DISCERNMENT", "ENCOURAGEMENT",
    "EVANGELISM", "FAITH", "GIVING", "HEALING", "HELPS", "HOSPITALITY",
    "INTERCESSION", "KNOWLEDGE", "LEADERSHIP", "MERCY", "MIRACLES",
    "PROPHECY", "SERVICE", "SHEPHERD", "TEACHING", "TONGUES", "WISDOM"
]


def generate_weighted_scores(top_gifts: list[str], secondary_gifts: list[str] = None) -> dict:
    """Generate realistic gift scores with specified top gifts getting higher scores."""
    scores = {}
    for gift in SPIRITUAL_GIFTS:
        if gift.upper() in [g.upper() for g in top_gifts]:
            # Top gifts: 28-35
            scores[gift] = random.randint(28, 35)
        elif secondary_gifts and gift.upper() in [g.upper() for g in secondary_gifts]:
            # Secondary gifts: 20-28
            scores[gift] = random.randint(20, 28)
        else:
            # Other gifts: 8-22
            scores[gift] = random.randint(8, 22)
    return scores


def generate_answers() -> dict:
    """Generate 80 random answers (1-5 scale)."""
    return {i: random.randint(1, 5) for i in range(1, 81)}


# Demo organization data
DEMO_ORGS = [
    {
        "name": "Grace Community Fellowship",
        "slug": "grace-community",
        "plan": "growth",
        "members": [
            {"name": "Pastor David Chen", "email": "david.chen@gracecommunity.org", "role": "admin", 
             "top_gifts": ["TEACHING", "LEADERSHIP"], "secondary": ["WISDOM", "SHEPHERD"]},
            {"name": "Sarah Mitchell", "email": "sarah.m@gracecommunity.org", "role": "admin",
             "top_gifts": ["ADMINISTRATION", "WISDOM"], "secondary": ["DISCERNMENT", "SERVICE"]},
            {"name": "Marcus Johnson", "email": "marcus.j@gracecommunity.org", "role": "user",
             "top_gifts": ["EVANGELISM", "ENCOURAGEMENT"], "secondary": ["FAITH", "HOSPITALITY"]},
            {"name": "Emily Rodriguez", "email": "emily.r@gracecommunity.org", "role": "user",
             "top_gifts": ["MERCY", "HOSPITALITY"], "secondary": ["HELPS", "INTERCESSION"]},
            {"name": "James Thompson", "email": "james.t@gracecommunity.org", "role": "user",
             "top_gifts": ["SERVICE", "GIVING"], "secondary": ["HELPS", "MERCY"]},
            {"name": "Priya Patel", "email": "priya.p@gracecommunity.org", "role": "user",
             "top_gifts": ["PROPHECY", "DISCERNMENT"], "secondary": ["WISDOM", "KNOWLEDGE"]},
            {"name": "Michael Brown", "email": "michael.b@gracecommunity.org", "role": "user",
             "top_gifts": ["FAITH", "HEALING"], "secondary": ["MIRACLES", "INTERCESSION"]},
        ]
    },
    {
        "name": "Harvest Point Church",
        "slug": "harvest-point",
        "plan": "enterprise",
        "members": [
            {"name": "Rev. Angela Williams", "email": "angela.w@harvestpoint.church", "role": "admin",
             "top_gifts": ["LEADERSHIP", "ENCOURAGEMENT"], "secondary": ["TEACHING", "SHEPHERD"]},
            {"name": "Thomas Lee", "email": "thomas.l@harvestpoint.church", "role": "admin",
             "top_gifts": ["ADMINISTRATION", "KNOWLEDGE"], "secondary": ["WISDOM", "DISCERNMENT"]},
            {"name": "Rachel Kim", "email": "rachel.k@harvestpoint.church", "role": "admin",
             "top_gifts": ["SHEPHERD", "TEACHING"], "secondary": ["MERCY", "ENCOURAGEMENT"]},
            {"name": "Daniel Okonkwo", "email": "daniel.o@harvestpoint.church", "role": "user",
             "top_gifts": ["MIRACLES", "FAITH"], "secondary": ["HEALING", "PROPHECY"]},
            {"name": "Sofia Martinez", "email": "sofia.m@harvestpoint.church", "role": "user",
             "top_gifts": ["HELPS", "HOSPITALITY"], "secondary": ["SERVICE", "MERCY"]},
            {"name": "Nathan Carter", "email": "nathan.c@harvestpoint.church", "role": "user",
             "top_gifts": ["APOSTLESHIP", "LEADERSHIP"], "secondary": ["EVANGELISM", "TEACHING"]},
            {"name": "Jessica Nguyen", "email": "jessica.n@harvestpoint.church", "role": "user",
             "top_gifts": ["INTERCESSION", "MERCY"], "secondary": ["DISCERNMENT", "HEALING"]},
            {"name": "Robert Davis", "email": "robert.d@harvestpoint.church", "role": "user",
             "top_gifts": ["EVANGELISM", "TONGUES"], "secondary": ["FAITH", "ENCOURAGEMENT"]},
            {"name": "Linda Jackson", "email": "linda.j@harvestpoint.church", "role": "user",
             "top_gifts": ["GIVING", "SERVICE"], "secondary": ["HOSPITALITY", "MERCY"]},
            {"name": "Kevin Moore", "email": "kevin.m@harvestpoint.church", "role": "user",
             "top_gifts": ["ENCOURAGEMENT", "DISCERNMENT"], "secondary": ["WISDOM", "SHEPHERD"]},
        ]
    }
]


def seed_database():
    """Seed the database with demo organizations, users, and surveys."""
    db = SessionLocal()
    
    try:
        print("🌱 Starting database seeding...")
        
        for org_data in DEMO_ORGS:
            # Check if org already exists
            existing_org = db.query(Organization).filter(Organization.slug == org_data["slug"]).first()
            if existing_org:
                print(f"⚠️  Organization '{org_data['name']}' already exists, skipping...")
                continue
            
            # Create organization
            org = Organization(
                name=org_data["name"],
                slug=org_data["slug"],
                plan=org_data["plan"],
                is_active=True
            )
            db.add(org)
            db.flush()  # Get the org ID
            
            print(f"✅ Created organization: {org.name} ({org.plan} plan)")
            
            for member_data in org_data["members"]:
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == member_data["email"]).first()
                if existing_user:
                    print(f"   ⚠️  User {member_data['email']} already exists, linking to org...")
                    existing_user.org_id = org.id
                    existing_user.role = member_data["role"]
                    user = existing_user
                else:
                    # Create user
                    user = User(
                        email=member_data["email"],
                        role=member_data["role"],
                        org_id=org.id,
                        created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                        last_login=datetime.utcnow() - timedelta(hours=random.randint(1, 168))
                    )
                    db.add(user)
                    db.flush()
                    print(f"   👤 Created user: {member_data['email']} ({member_data['role']})")
                
                # Create 1-3 surveys for each user
                num_surveys = random.randint(1, 3)
                for i in range(num_surveys):
                    survey_date = datetime.utcnow() - timedelta(days=random.randint(1, 180))
                    
                    survey = Survey(
                        user_id=user.id,
                        neon_user_id=member_data["email"],
                        org_id=org.id,
                        answers=generate_answers(),
                        scores=generate_weighted_scores(
                            member_data["top_gifts"],
                            member_data.get("secondary", [])
                        ),
                        created_at=survey_date
                    )
                    db.add(survey)
                
                print(f"      📊 Created {num_surveys} survey(s)")
        
        db.commit()
        print("\n🎉 Database seeding completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


def clear_demo_data():
    """Remove demo organizations and their data (for cleanup)."""
    db = SessionLocal()
    
    try:
        demo_slugs = [org["slug"] for org in DEMO_ORGS]
        
        for slug in demo_slugs:
            org = db.query(Organization).filter(Organization.slug == slug).first()
            if org:
                # Delete surveys associated with this org
                db.query(Survey).filter(Survey.org_id == org.id).delete()
                # Delete users associated with this org
                db.query(User).filter(User.org_id == org.id).delete()
                # Delete the org
                db.delete(org)
                print(f"🗑️  Deleted organization: {org.name}")
        
        db.commit()
        print("\n✅ Demo data cleared successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error clearing demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed database with demo organization data")
    parser.add_argument("--clear", action="store_true", help="Clear demo data instead of seeding")
    args = parser.parse_args()
    
    if args.clear:
        clear_demo_data()
    else:
        seed_database()
