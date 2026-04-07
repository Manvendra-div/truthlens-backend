from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ENV = os.getenv("ENV")

print(DATABASE_URL)

Base = declarative_base()

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,       # ✅ async session
    autocommit=False,
    autoflush=False,
    expire_on_commit=False     # ✅ needed for async — prevents lazy load errors
)

async def get_db():
    async with AsyncSessionLocal() as session:  # ✅ properly opens and closes
        yield session