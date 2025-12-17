"""
Spiritual Gifts Assessment Backend API.

This is the main entry point that imports from the app package.
For deployment, use: uvicorn main:app --host 0.0.0.0 --port 8000
"""
from app.main import app

# Re-export for uvicorn
__all__ = ["app"]
