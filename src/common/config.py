
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "RIA"
    PROJECT_VERSION: str = "1.0.0"
    
    # DATABASE
    # Will be overwritten by Supabase URL later
    # WARNING: Do not hardcode password here. Use .env
    DATABASE_URL: str = os.getenv("DATABASE_URL")



    # SECURITY
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key_change_me_in_prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 
    
    # STRIPE
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # STRIPE PRICES (Generated)
    STRIPE_PRICE_BASIC: str = "price_1SfcliFnZdVKZ5sTxnYViaIz"
    STRIPE_PRICE_BUSINESS: str = "price_1SfcliFnZdVKZ5sTpXborfk3"
    STRIPE_PRICE_ENTERPRISE: str = "price_1SfcljFnZdVKZ5sTpWMGntvr"

settings = Settings()
