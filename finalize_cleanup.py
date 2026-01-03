import os
import glob
import re
import random
import string
from datetime import datetime

ALEMBIC_DIR = "alembic/versions"
TEMP_FILES = [
    "check_db_config.py", "debug_schema_write.py", "backend_schema_check.txt",
    "migrate_native.py", "migration_log.txt", "migrate_postgres.py",
    "logs_out.txt", "list_audit_logs.py", "check_postgres_schema.py",
    "python_logs_out.txt", "test_log.py", "capture_db_url.py",
    "db_config_capture.txt", "pg_migration.log", "fix_log.txt",
    "tests/test_postgres_schema.py", "tests/test_migration_force.py",
    "tests/test_audit_repro.py"
]

def find_head():
    revisions = {}
    down_revs = set()
    
    files = glob.glob(os.path.join(ALEMBIC_DIR, "*.py"))
    for f in files:
        with open(f, "r") as pyf:
            content = pyf.read()
            rev_match = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", content)
            down_match = re.search(r"down_revision\s*=\s*['\"]([^'\"]+)['\"]", content)
            
            if rev_match:
                rev = rev_match.group(1)
                down = down_match.group(1) if down_match else None
                revisions[rev] = down
                if down:
                    down_revs.add(down)
                    
    # Head is the revision that is not in down_revs
    heads = [r for r in revisions if r not in down_revs]
    if len(heads) != 1:
        print(f"Warning: Found {len(heads)} heads: {heads}")
        # If multiple, assume the one added last alphabetically or just pick one (risky).
        # Usually checking dates in filename helps, but here we only see hashes.
        # Let's hope for 1.
        return heads[0] if heads else None
    return heads[0]

def create_migration(head_rev):
    new_rev = "".join(random.choices("0123456789abcdef", k=12))
    filename = f"{new_rev}_add_details_to_audit_logs.py"
    path = os.path.join(ALEMBIC_DIR, filename)
    
    content = f"""\"\"\"add details to audit_logs

Revision ID: {new_rev}
Revises: {head_rev}
Create Date: {datetime.now()}

\"\"\"
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '{new_rev}'
down_revision = '{head_rev}'
branch_labels = None
depends_on = None


def upgrade():
    # Only add if not exists (redundancy for safety if run on already fixed DB)
    # But Alembic standard is just add.
    # Since we manually fixed Prod, running this might fail if we don't check existence.
    # However, standard migration scripts assume they are the source of truth.
    # We can use 'column_exists' check code or suppress error.
    # Better: Use 'if not exists' in raw SQL or basic op.add_column.
    # op.add_column('audit_logs', sa.Column('details', sa.JSON(), nullable=True))
    
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c['name'] for c in insp.get_columns('audit_logs')]
    if 'details' not in columns:
        op.add_column('audit_logs', sa.Column('details', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('audit_logs', 'details')
"""
    with open(path, "w") as f:
        f.write(content)
    print(f"Created migration: {path}")

def cleanup():
    for f in TEMP_FILES:
        try:
            if os.path.exists(f):
                os.remove(f)
                print(f"Deleted {f}")
        except Exception as e:
            print(f"Error deleting {f}: {e}")

if __name__ == "__main__":
    print("Finding head...")
    head = find_head()
    print(f"Head: {head}")
    if head:
        create_migration(head)
    cleanup()
