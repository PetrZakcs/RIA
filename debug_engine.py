import asyncio
from src.harvester.api_engine import SrealityApiEngine

async def test_engine():
    print("Initializing Engine...")
    engine = SrealityApiEngine()
    
    # 1. Test Specific City (Prague)
    print("\n--- TEST 1: Prague (Region 10) ---")
    data_praha = await engine.search_apartments(region_id=10, region_type='region', limit=5)
    print(f"Praha Results: {len(data_praha)}")
    if data_praha:
        print(f"Sample: {data_praha[0].title} - {data_praha[0].price_raw}")

    # 2. Test Universal (Whole CZ)
    print("\n--- TEST 2: Universal (No Region) ---")
    # Using params that app.py would pass for "byt v cr" -> region_id=None
    data_cz = await engine.search_apartments(
        region_id=None, 
        region_type=None, 
        limit=5,
        region_text="Chomutov" 
    )
    print(f"Chomutov Results: {len(data_cz)}")
    print(f"Whole CZ Results: {len(data_cz)}")
    
    if data_cz:
        print("--- Testing Pipeline on First Item ---")
        try:
            from src.cleaner.pipeline import DataCleaner
            from src.cleaner.enrichment import Enricher
            from src.reporting.analysis import FinancialAnalyst
            
            cleaner = DataCleaner()
            enricher = Enricher()
            analyst = FinancialAnalyst()
            
            raw = data_cz[0]
            print(f"Processing: {raw.title}")
            
            clean = cleaner.process_ad(raw)
            print(f"Cleaned: {clean.title} | Price: {clean.price_czk}")
            
            enriched = await enricher.enrich_location(clean)
            print(f"Enriched Loc: {enriched.locality}")
            
            metrics = analyst.evaluate(enriched)
            print(f"Metrics: Yield {metrics.gross_yield_percent}%")
            print("PIPELINE SUCCESS")
            
        except Exception as e:
            print(f"PIPELINE FAILED: {e}")
            import traceback
            traceback.print_exc()

    await engine.close()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_engine())
