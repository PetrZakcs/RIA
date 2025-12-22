import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from .session import Base



class Property(Base):
    """
    Represents a unique real estate listing.
    """
    __tablename__ = "properties"

    hash_id = Column(Integer, primary_key=True, index=True) # Sreality unique ID
    source = Column(String, default="sreality") # sreality, idnes, etc.
    
    title = Column(String)
    location_raw = Column(String)
    category_main = Column(Integer) # 1=Apt, 2=House...
    category_sub = Column(Integer) # Layout ID etc.
    
    # Track Prices
    current_price = Column(Integer)
    price_per_m2 = Column(Integer, nullable=True)
    floor_area = Column(Integer, nullable=True)
    
    # Timestamps
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata / JSON
    raw_data = Column(String, nullable=True) # JSON store for future proofing
    
class PriceHistory(Base):
    """
    Tracks price changes over time.
    """
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, index=True) # ForeignKey to Property.hash_id (but implicit for now to avoid complexity with BigInt PKs if different sources overlap. Using hash_id is fine for Sreality)
    price = Column(Integer)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

