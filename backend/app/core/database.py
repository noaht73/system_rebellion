from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import create_engine
from app.core.base import Base

# Database URLs
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./system_rebellion.db"
SYNC_DATABASE_URL = "sqlite:///./system_rebellion.db?check_same_thread=False"

# Create engines
async_engine = create_async_engine(
    ASYNC_DATABASE_URL, 
    echo=True,  # Logging for debugging
    future=True,
    pool_pre_ping=True  # Ensure connections are valid
)
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=True,  # Logging for debugging
    future=True,
    pool_pre_ping=True,  # Ensure connections are valid
    connect_args={"check_same_thread": False, "timeout": 30}  # Allow thread sharing
)
# Async session
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Sync session - now properly bound to the sync engine
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False, 
    autoflush=False
)
def log_registered_models():
    """
    Sir Hawkington's Model Inspection Protocol
    The Meth Snail's paranoid sketched-out ass watches ALL!
    """
    print("REGISTERED MODELS")
    print("\n")
    for table_name in Base.metadata.tables.keys():
        print(f"The Meth Snail Found Model: {table_name}")
    print("\n")
#Model Creation Funciton
async def init_models():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log_registered_models()
    print("Models initialized successfully.")

# Async database getter
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

# Sync database getter
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# For backwards compatibility, make get_db the default
# This allows existing code to work without changes
get_db_dependency = get_db
