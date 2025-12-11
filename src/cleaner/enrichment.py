from src.cleaner.models import CleanPropertyAd
import random
from loguru import logger

class Enricher:
    """
    Mock implementation for Geocoding and external data APIs.
    In production, this would call Google Maps API / mapy.cz API using an async client.
    """
    
    async def enrich_location(self, ad: CleanPropertyAd) -> CleanPropertyAd:
        # Mock geocoding
        # In MVP we don't have real API keys yet
        logger.debug(f"Geocoding address for {ad.source_url}...")
        
        # Simulating finding coordinates for Prague
        ad.latitude = 50.0755 + (random.random() - 0.5) * 0.1
        ad.longitude = 14.4378 + (random.random() - 0.5) * 0.1
        
        # Mock distance calculation
        ad.dist_center_km = round(random.uniform(1.0, 15.0), 1)
        ad.district = "Praha - MockDistrict"
        
        return ad
