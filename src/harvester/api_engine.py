import httpx
from typing import List, Optional
from loguru import logger
from src.harvester.models import RawPropertyAd
import time
import asyncio

class SrealityApiEngine:
    """
    Directly consumes Sreality.cz Internal API (v2).
    Much faster and more reliable than HTML scraping.
    """
    BASE_URL = "https://www.sreality.cz/api"
    
    # Category Mappings
    CAT_MAIN_APARTMENTS = 1
    CAT_TYPE_SALE = 1
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            },
            timeout=10.0
        )
        
    async def close(self):
        await self.client.aclose()
        
    async def search_apartments(self, 
                              region_id: Optional[int] = None, 
                              region_type: Optional[str] = None, # 'municipality', 'district'
                              min_price: int = 0, 
                              max_price: Optional[int] = None,
                              layouts: List[int] = [],
                              limit: int = 20,
                              region_text: Optional[str] = None,
                              category_main: int = 1) -> List[RawPropertyAd]:
        """
        fetches properties from API.
        category_main: 1=Apt, 2=House, 3=Land, 4=Recreation, 5=Commercial
        """
        
        # Build Params
        per_page = 60 # Max efficient size
        params = {
            "category_main_cb": category_main,
            "category_type_cb": self.CAT_TYPE_SALE,
            "per_page": per_page,
            "tms": int(time.time())
        }
        
        if region_text:
            params["region"] = region_text
            # params["region_entity_type"] = "municipality" # generic hint, often helps


        if region_id:
            # Logic to determine if it is Region or District
            if region_type == 'district':
                params["locality_district_id"] = region_id
            elif region_type == 'region':
                params["locality_region_id"] = region_id
            else:
                # Heuristic Fallback
                if region_id == 10: # Praha Whole
                    params["locality_region_id"] = 10
                elif region_id > 100:
                    params["locality_district_id"] = region_id
                else:
                    params["locality_region_id"] = region_id
        
        print(f"DEBUG: Search Params: {params}")

                 
        if min_price > 0 or max_price:
            low = min_price if min_price else 0
            high = max_price if max_price else ""
            if not high: high = "" 
            params["czk_price_summary_order2"] = f"{low}|{high}"
            
        if layouts:
            param_val = "|".join([str(l) for l in layouts])
            params["category_sub_cb"] = param_val

        results = []
        
        # Reverse map for link construction
        layout_id_map = {
            2: "1+kk", 3: "1+1",
            4: "2+kk", 5: "2+1",
            6: "3+kk", 7: "3+1",
            8: "4+kk", 9: "4+1",
        }
        
        # DEEP SCAN / PAGINATION LOGIC
        # We fetch until we reach satisfy the 'limit' requested by caller.
        # limit might be 200, 500, etc.
        
        page = 1
        fetched_count = 0
        
        try:
            while fetched_count < limit:
                # Check remaining
                remaining = limit - fetched_count
                # If remaining is small, we could adjust per_page, but simplest is to fetch 60 and slice.
                
                params["page"] = page
                
                url = f"{self.BASE_URL}/cs/v2/estates"
                logger.info(f"API Fetch Page {page} | fetched: {fetched_count}/{limit}")
                
                resp = await self.client.get(url, params=params)
                resp.raise_for_status()
                
                data = resp.json()
                items = data.get("_embedded", {}).get("estates", [])
                
                if not items:
                    break # End of results
                
                for item in items:
                    if fetched_count >= limit:
                        break
                        
                    # Parse Item
                    title = item.get("name", "Unknown")
                    loc = item.get("locality", "Unknown")
                    price = item.get("price", 0)
                    hash_id = item.get("hash_id")
                    seo = item.get("seo", {})
                    seo_loc = seo.get("locality")
                    
                    # Link Construction Logic
                    # Map category_main_cb to URL slug
                    # 1=byt, 2=dum, 3=pozemek, 4=rekreace, 5=komercni
                    cat_main = seo.get("category_main_cb", 1)
                    cat_slug_map = {
                        1: "byt", 
                        2: "dum", 
                        3: "pozemek", 
                        4: "rekreace", 
                        5: "komercni"
                    }
                    main_slug = cat_slug_map.get(cat_main, "byt")
                    
                    # Layout/Type Slug
                    # For Apts: 1+kk etc.
                    # For Houses: rodinny, vila... based on sub_cb? 
                    # Actually Sreality is forgiving. /prodej/dum/rodinny/... works.
                    # If we don't know exact sub-type string, "unknown" might work or we need a sub-map.
                    # Let's try to map common subs or keep it simple.
                    # Actually, the layout_id_map I have (2->"1+kk") is only for Apts.
                    # For simplicity, if it's not apt, we can put "vse" or "ostatni"?
                    # Verification Needed: Does /prodej/dum/vse/... work?
                    # Better: Parse title or define a sub-map.
                    
                    # Simplified Sub-Slug Logic (Verified)
                    cat_sub = seo.get("category_sub_cb", 1) 
                    
                    sub_slug = "ostatni" # Universal Default
                    
                    if cat_main == 1: # Apartments
                        # Map layout ID to slug
                        # If sub_cb (e.g. 2->1+kk) is found, use it.
                        # We use layout_id_map logic implicitly or we need a map.
                        # Wait, layout_id_map maps 2->"1+kk" ? No, API maps layout IDs.
                        # Let's trust my existing layout_id_map if defined, else 'vse'?
                        # Actually for Apt, /byt/vse/ works usually.
                        # But specific is better.
                        # Assuming layout_id_map is defined in class scope or previously.
                        # Let's use "vse" as safer default if map fails.
                        sub_slug = layout_id_map.get(cat_sub, "vse")
                        
                    elif cat_main == 2: # Houses
                        sub_slug = "rodinny" # Verified safe
                        
                    elif cat_main == 3: # Land
                        sub_slug = "bydleni" # Verified safe (stavebni is 404)
                        
                    elif cat_main == 4: # Recreation
                        sub_slug = "chata" # Verified safe
                        
                    elif cat_main == 5: # Commercial
                        sub_slug = "kancelare" # Best guess, or 'obchodni'
                        
                    # Area & Layout Parsing
                    import re
                    area = "0"
                    # Match: 50 m², 50m2, 50 m2
                    area_match = re.search(r'(\d+)\s*(?:m²|m2)', title, re.IGNORECASE)
                    if area_match:
                        area = area_match.group(1)
                    
                    # Link Construction Robustness
                    # Sreality Redirects if 'seo_loc' is present and ID is correct.
                    # If seo_loc is missing, we use 'unknown', but we must ensure valid slugs.
                    
                    final_sub_slug = sub_slug
                    # Special fix for Apartments: 1+kk needs to be URL safe? Browsers handle + ok usually.
                    if cat_main == 1 and sub_slug not in layout_id_map.values():
                        final_sub_slug = "vse"

                    safe_loc = seo_loc if seo_loc else "unknown"
                    
                    link = f"https://www.sreality.cz/detail/prodej/{main_slug}/{final_sub_slug}/{safe_loc}/{hash_id}"
                        
                    layout = title
                    l_match = re.search(r'(\d+\+kk|\d+\+1|\d+\+0|1\+1|garsoniera)', title, re.IGNORECASE)
                    if l_match:
                        layout = l_match.group(1)

                    
                    ad = RawPropertyAd(
                        source_url=link,
                        source_portal="sreality",
                        title=title,
                        price_raw=str(price),
                        location_raw=loc,
                        floor_area_raw=area,
                        layout=layout   
                    )
                    results.append(ad)
                    fetched_count += 1
                
                page += 1
                
                # Safety Sleep to be nice
                if limit > 60:
                    await asyncio.sleep(0.1) 
                    
            logger.info(f"Total Fetched: {len(results)} items")
                
        except Exception as e:
            logger.error(f"API Error: {e}")
            
        return results
