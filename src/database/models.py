import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from .session import Base

class SubscriptionTier(str, enum.Enum):
    BASIC = "BASIC"
    BUSINESS = "BUSINESS"
    ENTERPRISE = "ENTERPRISE"
    LTD = "LTD"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    # Subscription & Payment
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.BASIC)
    is_active = Column(Boolean, default=True)
    stripe_customer_id = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
