import sys
import os
from datetime import datetime

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.database.session import engine, Base, SessionLocal
from src.database.models import Property, PriceHistory
from src.harvester.ingestion import IngestionService
from src.harvester.models import RawPropertyAd

def verify():
    print("--- 1. Init DB ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    svc = IngestionService(db)

    print("--- 2. Create Mock Ad ---")
    ad = RawPropertyAd(
        hash_id=12345,
        source_url="http://test",
        source_portal="sreality",
        title="Test Flat",
        price_raw="5000000",
        location_raw="Prague",
        floor_area_raw="50"
    )
    
    print(f"Ingesting: {ad.title} @ {ad.price_raw}")
    svc.process_batch([ad])
    
    # Verify 1
    prop = db.query(Property).filter(Property.hash_id==12345).first()
    assert prop is not None
    assert prop.current_price == 5000000
    assert db.query(PriceHistory).count() == 1
    print("Version 1 Saved OK.")
    
    print("--- 3. Update Price ---")
    ad_v2 = RawPropertyAd(
        hash_id=12345,
        source_url="http://test",
        source_portal="sreality",
        title="Test Flat Updated",
        price_raw="4500000", # Discount
        location_raw="Prague",
        floor_area_raw="50"
    )
    
    print(f"Ingesting Update: {ad_v2.title} @ {ad_v2.price_raw}")
    svc.process_batch([ad_v2])
    
    # Verify 2
    prop = db.query(Property).filter(Property.hash_id==12345).first()
    assert prop.current_price == 4500000
    assert prop.title == "Test Flat Updated"
    
    hist_count = db.query(PriceHistory).count()
    assert hist_count == 2
    print(f"History Count: {hist_count} (Expected 2)")
    
    histories = db.query(PriceHistory).all()
    for h in histories:
        print(f" - History: {h.price} @ {h.detected_at}")

    print("SUCCESS: Ingestion Logic Verified.")

if __name__ == "__main__":
    verify()
