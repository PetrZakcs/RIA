import asyncio
from loguru import logger
from src.harvester.models import RawPropertyAd
from src.cleaner.pipeline import DataCleaner
from src.cleaner.enrichment import Enricher
from src.cleaner.models import CleanPropertyAd

async def run_cleaner_pipeline(raw_ads: list[RawPropertyAd]) -> list[CleanPropertyAd]:
    cleaner = DataCleaner()
    enricher = Enricher()
    
    cleaned_ads = []
    
    for raw in raw_ads:
        try:
            # 1. Cleaning
            clean = cleaner.process_ad(raw)
            
            # 2. Enrichment (Async)
            clean = await enricher.enrich_location(clean)
            
            cleaned_ads.append(clean)
            logger.info(f"Cleaned & Enriched: {clean.price_czk} CZK, {clean.floor_area_m2}m2, Dist: {clean.dist_center_km}km")
            
        except Exception as e:
            logger.error(f"Error processing ad {raw.source_url}: {e}")
            
    return cleaned_ads

if __name__ == "__main__":
    # Test run
    dummy_raw = RawPropertyAd(
        source_url="http://test.com",
        source_portal="test",
        title="Pěkný byt 2+kk",
        price_raw="7 500 000 Lei", # Intentional typo/currency
        floor_area_raw="55 metrů",
        layout="2+kk"
    )
    
    asyncio.run(run_cleaner_pipeline([dummy_raw]))
