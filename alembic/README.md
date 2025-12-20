# Database Migrations with Alembic

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

## Quick Start

### Generate a new migration after model changes:
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations to database:
```bash
alembic upgrade head
```

### Rollback last migration:
```bash
alembic downgrade -1
```

### View migration history:
```bash
alembic history
```

## Development vs Production

- **Development**: `ENV=development` → Uses `create_all()` for convenience
- **Production**: `ENV=production` → Use Alembic migrations (`alembic upgrade head`)

## First-time Setup

If starting fresh with an empty database:
```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## Configuration

Database URL is read from `app/config.py` which loads from `.env`:
- See `.env.example` for required environment variables
