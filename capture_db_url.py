from app.config import settings
import os

def capture_config():
    with open("db_config_capture.txt", "w") as f:
        f.write(f"URL={settings.DATABASE_URL}\n")

if __name__ == "__main__":
    capture_config()
