# from sqlalchemy import create_engine # for synch operation 
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine # for Asynch operation 
from sqlalchemy.orm import DeclarativeBase  # sessionmaker

from config import settings

# For sqllite
# SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"
# engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# for Postgres
engine = create_async_engine(settings.database_url)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # (autoflush=False, autocommit=False, bind=engine)

class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session