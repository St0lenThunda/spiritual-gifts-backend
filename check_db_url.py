from app.config import settings
with open("db_url_output.txt", "w") as f:
    f.write(f"DATABASE_URL: {settings.DATABASE_URL}\n")
