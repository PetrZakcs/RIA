import asyncio
import sys
import os
import unicodedata
import re

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd()))
from src.harvester.api_engine import SrealityApiEngine

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().replace(" ", "-")

KNOWN_LOCATIONS = {
    # Updated to match app.py logic
    "ceska republika": (-99, 'region'), "cr": (-99, 'region'), "cz": (-99, 'region'),
    
    # Specific Cities
    "brno": (72, 'district'),
    
    # Regions
    "jihocesky": (1, 'region'), "budejovice": (1, 'region'),
    "plzensky": (2, 'region'), "plzen": (2, 'region'),
    "karlovarsky": (3, 'region'), "vary": (3, 'region'),
    "ustecky": (4, 'region'), "usti": (4, 'region'),
    "liberecky": (5, 'region'), "liberec": (5, 'region'),
    "kralovehradecky": (6, 'region'), "hradec": (6, 'region'),
    "pardubicky": (7, 'region'), "pardubice": (7, 'region'),
    "olomoucky": (8, 'region'), "olomouc": (8, 'region'),
    "zlinsky": (9, 'region'), "zlin": (9, 'region'),
    "praha": (10, 'region'),
    "stredocesky": (11, 'region'),
    "moravskoslezsky": (12, 'region'), "ostrava": (12, 'region'),
    "vysocina": (13, 'region'), "jihlava": (13, 'region'),
    "jihomoravsky": (14, 'region'),
}

async def interactive_search():
    print("--- RIA CLI Search (Experimental) ---")
    print("Type a location to search (e.g. 'Brno', 'Plzen', 'Ceska Republika').")
    print("Type 'exit' to quit.\n")
    
    engine = SrealityApiEngine()
    
    try:
        while True:
            query = input("Search > ").strip()
            if not query: continue
            if query.lower() in ["exit", "quit", "q"]: break
            
            # Parse Location
            slug = slugify(query)
            region_id = -1 
            region_type = None

            for name, val in KNOWN_LOCATIONS.items():
                if name in slug:
                    # Handle Tuple vs Int (for robustness)
                    if isinstance(val, tuple):
                        r_id, r_type = val
                    else:
                         r_id, r_type = val, 'region'
                    
                    if r_id == -99:
                        region_id = None
                    else:
                        region_id = r_id
                        region_type = r_type
                    break
            
            # Special case for None (Whole CZ)
            if region_id == -1 and any(x in slug for x in ["ceska", "repu", "cr"]):
                 region_id = None
                 print(f"   -> Detected: Whole Czech Republic")
            elif region_id != -1:
                 print(f"   -> Detected Region ID: {region_id} (Type: {region_type})")
            else:
                 print("   -> Unknown location, defaulting to Whole Country (None)")
                 region_id = None
                 
            # Search
            print("   -> Fetching data...")
            results = await engine.search_apartments(
                region_id=region_id, 
                region_type=region_type,
                max_price=None, 
                layouts=[]
            )
            
            print(f"   -> Found {len(results)} listings.")
            for i, res in enumerate(results[:5]):
                 print(f"      {i+1}. {res.title} | {res.price_raw} | {res.location_raw}")
            if len(results) > 5:
                print("      ... and more.")
            print("-" * 30)
            
    finally:
        await engine.close()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_search())
    except KeyboardInterrupt:
        print("\nGoodbye!")
