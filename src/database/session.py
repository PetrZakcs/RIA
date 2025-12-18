from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.common.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

if not SQLALCHEMY_DATABASE_URL:
    # Fallback or Error? For Vercel, this must be set.
    # We'll default to in-memory sqlite for safety if missing, to avoid instant crash, 
    # but likely will fail later.
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
