import os
from dotenv import load_dotenv

def check_env(path):
    print(f"Checking {path}")
    if os.path.exists(path):
        load_dotenv(path, override=True)
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            print(f"DATABASE_URL: {db_url[:30]}...")
        else:
            print("DATABASE_URL not found in env")
    else:
        print("File not found")

check_env("/home/thunda/Dev/543_Tools/spiritual-gifts/backend/.env")
check_env("/home/thunda/Dev/543_Tools/spiritual_gifts_backend/.env")
