import re
from loguru import logger
from src.harvester.models import RawPropertyAd
from src.cleaner.models import CleanPropertyAd, PropertyType

class DataCleaner:
    @staticmethod
    def parse_price(raw_price: str) -> float | None:
        if not raw_price:
            return None
        # Remove non-numeric except digits
        # Example: "5 490 000 Kč" -> 5490000
        clean_str = re.sub(r'[^\d]', '', raw_price)
        try:
            return float(clean_str)
        except ValueError:
            return None

    @staticmethod
    def parse_area(raw_area: str) -> float | None:
        if not raw_area:
            return None
        # Example: "65 m²" -> 65
        clean_str = re.sub(r'[^\d]', '', raw_area)
        try:
            return float(clean_str)
        except ValueError:
            return None
            
    def process_ad(self, raw: RawPropertyAd) -> CleanPropertyAd:
        # Basic parsing
        price = self.parse_price(raw.price_raw)
        area = self.parse_area(raw.floor_area_raw)
        
        # Simple layout extraction
        layout = None
        if raw.layout:
            layout = raw.layout.strip()
            
        clean_ad = CleanPropertyAd(
            source_url=raw.source_url,
            source_portal=raw.source_portal,
            price_czk=price,
            floor_area_m2=area,
            layout_normalized=layout,
            # Defaults
            property_type=PropertyType.APARTMENT 
        )
        
        # Derived metrics
        clean_ad.calculate_price_per_m2()
        
        return clean_ad
