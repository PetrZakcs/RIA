import datetime
from sqlalchemy.orm import Session
from src.database.models import Property, PriceHistory
from src.harvester.models import RawPropertyAd
from loguru import logger
import json

class IngestionService:
    def __init__(self, db: Session):
        self.db = db

    def process_batch(self, ads: list[RawPropertyAd]):
        """
        Upserts properties and tracks price history.
        """
        count_new = 0
        count_updated = 0
        count_price_changed = 0

        for ad in ads:
            # 1. Check existence
            existing = self.db.query(Property).filter(Property.hash_id == ad.hash_id).first()
            
            # Safe parsing
            try:
                price_val = int(float(ad.price_raw)) if ad.price_raw else 0
                area_val = int(ad.floor_area_raw) if ad.floor_area_raw and ad.floor_area_raw.isdigit() else None
            except:
                price_val = 0
                area_val = None

            if not existing:
                # CREATE
                new_prop = Property(
                    hash_id=ad.hash_id,
                    source=ad.source_portal,
                    title=ad.title,
                    location_raw=ad.location_raw,
                    # category_main etc. need to be passed or parsed? 
                    # For now we might not have them in RawPropertyAd explicit fields?
                    # ad.layout is present.
                    current_price=price_val,
                    floor_area=area_val,
                    raw_data=ad.json()
                )
                self.db.add(new_prop)
                self.db.commit() # Commit to get ID? hash_id is PK.
                
                # History Init
                hist = PriceHistory(
                    property_id=ad.hash_id,
                    price=price_val
                )
                self.db.add(hist)
                count_new += 1
            else:
                # UPDATE
                existing.last_seen_at = datetime.datetime.now()
                existing.title = ad.title # Update title if changed
                
                # Check Price
                if existing.current_price != price_val:
                    logger.info(f"Price Change {existing.hash_id}: {existing.current_price} -> {price_val}")
                    # Record History
                    hist = PriceHistory(
                        property_id=existing.hash_id,
                        price=price_val
                    )
                    self.db.add(hist)
                    
                    existing.current_price = price_val
                    count_price_changed += 1
                
                count_updated += 1
        
        self.db.commit()
        logger.info(f"Ingestion: New={count_new}, Upd={count_updated}, PriceChg={count_price_changed}")
