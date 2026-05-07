from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

DATABASE_URL = "sqlite+aiosqlite:///./buywise.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    from backend.models import Review  # noqa: F401
    async with engine.begin() as conn:
        # Create tables (no-op for existing tables)
        await conn.run_sync(Base.metadata.create_all)

        # Safe migration: add new columns if they don't already exist
        for col_def in [
            "ALTER TABLE reviews ADD COLUMN source_url TEXT",
            "ALTER TABLE reviews ADD COLUMN images TEXT",
        ]:
            try:
                await conn.execute(text(col_def))
            except Exception:
                pass  # Column already exists — ignore
