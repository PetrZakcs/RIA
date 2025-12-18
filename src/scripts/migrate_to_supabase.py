
import os
import sys
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
# Fix path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.database.models import Base, User
from src.common.config import settings

def migrate(postgres_url: str):
    print("🚀 Starting Migration: SQLite -> Supabase")
    
    # 1. SQLite Source
    sqlite_url = "sqlite:///ria.db"
    if not os.path.exists("ria.db"):
        print("❌ ria.db not found!")
        return
        
    engine_sqlite = create_engine(sqlite_url)
    SessionSQLite = sessionmaker(bind=engine_sqlite)
    session_sqlite = SessionSQLite()
    
    # 2. Postgres Target
    print(f"🔹 Target: {postgres_url.split('@')[-1]}") # Hide password
    engine_pg = create_engine(postgres_url)
    SessionPG = sessionmaker(bind=engine_pg)
    session_pg = SessionPG()
    
    # 3. Create Tables in Postgres
    print("🔹 Creating tables in Supabase...")
    Base.metadata.create_all(engine_pg)
    
    # 4. Fetch Users
    users = session_sqlite.query(User).all()
    print(f"🔹 Found {len(users)} users in SQLite.")
    
    # 5. Insert to Postgres
    count = 0
    for u in users:
        # Check if exists
        exists = session_pg.query(User).filter_by(email=u.email).first()
        if not exists:
            new_user = User(
                email=u.email,
                hashed_password=u.hashed_password,
                full_name=u.full_name,
                subscription_tier=u.subscription_tier,
                is_active=u.is_active,
                stripe_customer_id=u.stripe_customer_id,
                created_at=u.created_at
            )
            session_pg.add(new_user)
            count += 1
            
    session_pg.commit()
    print(f"✅ Migration Complete! Transferred {count} new users.")

if __name__ == "__main__":
    # Get URL from Env or Args
    url = os.getenv("DATABASE_URL")
    if len(sys.argv) > 1:
        url = sys.argv[1]
        
    if not url:
        print("❌ Error: No DATABASE_URL provided.")
        print("Usage: python migrate_to_supabase.py <POSTGRES_URL>")
        sys.exit(1)
        
    migrate(url)
