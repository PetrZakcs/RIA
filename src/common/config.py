from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Base
    PROJECT_NAME: str = "RIA - Real Estate Investment Agent"
    VERSION: str = "0.1.0"
    
    # Database
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "ria_raw"
    POSTGRES_URI: str = "postgresql://user:password@localhost:5432/ria_core"
    
    # Scraper
    HEADLESS: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
