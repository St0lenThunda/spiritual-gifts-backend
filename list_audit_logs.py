from sqlalchemy import text
from app.database import engine
from app.models import AuditLog
from sqlalchemy.orm import Session
import sys

def list_logs():
    output_file = "/home/thunda/Dev/543_Tools/spiritual-gifts/backend/python_logs_out.txt"
    with open(output_file, "w") as f:
        f.write(f"Checking for audit logs in {engine.url}\n")
        try:
            with Session(engine) as session:
                count = session.query(AuditLog).count()
                f.write(f"Total Audit Logs: {count}\n")
                
                logs = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(5).all()
                for log in logs:
                    f.write(f" - [{log.timestamp}] {log.action} (Org: {log.org_id}) Details: {log.details}\n")
        except Exception as e:
            f.write(f"Error querying logs: {e}\n")

if __name__ == "__main__":
    list_logs()
