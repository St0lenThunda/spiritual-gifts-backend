import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User
from app.config import settings

def main():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        user = session.query(User).filter_by(email='tonym415@gmail.com').first()
        if user:
            print(f"User: {user.email}, role: {user.role}")
        else:
            print('User not found')

if __name__ == '__main__':
    main()
