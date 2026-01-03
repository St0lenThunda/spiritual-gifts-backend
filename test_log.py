import os
print("Starting test_log...")
try:
    with open("pg_migration.log", "w") as f:
        f.write("Test log content.\n")
    print("Log written.")
except Exception as e:
    print(f"Error writing: {e}")

try:
    import app
    print(f"App imported: {app}")
except ImportError as e:
    print(f"ImportError: {e}")
