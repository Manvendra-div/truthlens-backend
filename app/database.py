from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ENV = os.getenv("ENV")

print(DATABASE_URL)

Base = declarative_base()

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()