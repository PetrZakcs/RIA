from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class PropertyType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    LAND = "land"
    UNKNOWN = "unknown"

class CleanPropertyAd(BaseModel):
    """
    Standardized property data ready for analysis.
    """
    # Identification
    source_url: str
    source_portal: str
    
    # Display Data
    title: Optional[str] = None
    locality: Optional[str] = None
    images: Optional[list[str]] = None
    
    # Core numeric data

    price_org_czk: Optional[float] = None # Cena původní
    price_czk: Optional[float] = None     # Cena (např. po slevě nebo očištěná)
    price_per_m2: Optional[float] = None
    
    floor_area_m2: Optional[float] = None
    land_area_m2: Optional[float] = None  # U domů
    
    # Classification
    property_type: PropertyType = PropertyType.UNKNOWN
    layout_normalized: Optional[str] = None # e.g. "3+kk"
    condition_rating: Optional[int] = None # 1-10 (1=ruin, 10=new)
    
    # Location (Enriched)
    address_display: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district: Optional[str] = None
    
    # Enriched data
    dist_center_km: Optional[float] = None
    
    def calculate_price_per_m2(self):
        if self.price_czk and self.floor_area_m2 and self.floor_area_m2 > 0:
            self.price_per_m2 = round(self.price_czk / self.floor_area_m2, 2)
