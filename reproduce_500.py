import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models import Organization, User, Survey
from app.services.survey_service import SurveyService
import uuid

# Setup DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_repro.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def repro():
    db = TestingSessionLocal()
    try:
        # 1. Setup
        org = Organization(name="Norm Org", slug=str(uuid.uuid4()))
        db.add(org)
        
        admin = User(email=f"admin_{uuid.uuid4()}@example.com", role="admin", membership_status="active")
        db.add(admin)
        db.flush()
        admin.org_id = org.id
        
        s1 = Survey(user_id=admin.id, org_id=org.id, answers={}, scores={"Administration": 20, "Faith": 25, "overall": 100})
        s2 = Survey(user_id=admin.id, org_id=org.id, answers={}, scores={"Administration": 18, "Mercy": 12, "Overall": 90}) 
        
        db.add_all([s1, s2])
        db.commit()
        
        # 3. Call Analytics
        print("Calling get_org_analytics...")
        result = SurveyService.get_org_analytics(db, org_id=org.id)
        print("Success!")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        if os.path.exists("./test_repro.db"):
            os.remove("./test_repro.db")

if __name__ == "__main__":
    repro()
