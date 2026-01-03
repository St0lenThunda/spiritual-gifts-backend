import sys
import os

print("Starting checks...", file=sys.stderr)
try:
    from app.config import settings
    print(f"DATABASE_URL={settings.DATABASE_URL}")
except Exception as e:
    print(f"Error loading config: {e}", file=sys.stderr)
except ImportError as e:
    print(f"ImportError: {e}", file=sys.stderr)
