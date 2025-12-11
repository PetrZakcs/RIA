import asyncio
from src.harvester.api_engine import SrealityApiEngine
import json

async def main():
    engine = SrealityApiEngine()
    
    print("-" * 50)
    print("TEST 1: Praha 2 (5002), 2kk (4), Max 5M CZK")
    results_strict = await engine.search_apartments(region_id=5002, layouts=[4], max_price=5000000)
    print(f"Found: {len(results_strict)}")
    for r in results_strict:
        print(f" - {r.title} ({r.price_raw} Kč) [{r.source_url}]")

    print("-" * 50)
    print("TEST 2: Praha 2 (5002), 2kk (4), UNLIMITED PRICE")
    results_open = await engine.search_apartments(region_id=5002, layouts=[4], max_price=None)
    print(f"Found: {len(results_open)}")
    if results_open:
        item = results_open[0]
        print(f"Sample: {item.title} ({item.price_raw} Kč) [{item.source_url}]")
        
    await engine.close()

if __name__ == "__main__":
    asyncio.run(main())
