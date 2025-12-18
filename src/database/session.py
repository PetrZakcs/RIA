from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from src.common.config import settings

# FORCE SQLITE (MEMORY) TO UNBLOCK VERCEL DEPLOYMENT
# User requested to disconnect Supabase for now.
# Data will be ephemeral (lost on restart), but app will run.
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args=connect_args,
    poolclass=NullPool
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
