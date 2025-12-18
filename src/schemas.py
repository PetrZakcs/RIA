from pydantic import BaseModel, EmailStr
from typing import Optional
from src.database.models import SubscriptionTier

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    subscription_tier: SubscriptionTier = SubscriptionTier.BASIC
    # Add stripe_token etc later

class UserResponse(UserBase):
    id: int
    subscription_tier: SubscriptionTier
    is_active: bool

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    subscription_tier: str

class TokenData(BaseModel):
    email: Optional[str] = None
