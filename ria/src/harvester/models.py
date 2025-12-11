from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class RawPropertyAd(BaseModel):
    """
    Represents raw data scraped from a real estate portal.
    Excludes complex validation, focused on capturing data as-is.
    """
    source_url: str
    source_portal: str
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    # Raw extracted fields (can be None if parsing fails)
    title: Optional[str] = None
    price_raw: Optional[str] = None  # e.g. "5 000 000 Kč"
    description: Optional[str] = None
    
    # Location data
    location_raw: Optional[str] = None
    
    # Parameters
    floor_area_raw: Optional[str] = None # e.g. "65 m2"
    layout: Optional[str] = None # e.g. "3+kk"
    
    # Extra metadata (images, energetic class, etc)
    images: list[str] = []
    attributes: Dict[str, Any] = {} # Flexible dict for other params

    class Config:
        arbitrary_types_allowed = True
