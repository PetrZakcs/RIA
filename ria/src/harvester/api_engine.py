import httpx
from typing import List, Optional
from loguru import logger
from src.harvester.models import RawPropertyAd
import time

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
                              layouts: List[int] = []) -> List[RawPropertyAd]:
        """
        fetches apartments from API.
        region_id: Internal Sreality ID (e.g. 5002 for Praha 2, 10 for Praha)
        """
        
        # Build Params
        params = {
            "category_main_cb": self.CAT_MAIN_APARTMENTS,
            "category_type_cb": self.CAT_TYPE_SALE,
            "per_page": 20,
            "tms": int(time.time())
        }
        
        if region_id:
            # Sreality differentiates region types in params
            # locality_region_id (Kraj), locality_district_id (Okres), locality_country_id...
            # This is complex. But often 'locality_district_id' covers cities like "Okres Brno-město"
            # For Prague districts "Praha 2", it is often 'locality_district_id' OR specialized.
            # Simplified MVP: Try passing it as 'region_entity_id' or mapped per type.
            
            # Heuristic based on common IDs:
            # 10 = Praha (Region) -> locality_region_id
            # 5001-5010 = Praha 1-10 (Districts?) -> actually these are often municipal parts.
            
            # Let's try generic query param 'locality_region_id' for broad, 'locality_district_id' for specific.
            # Safe bet: If ID < 100 it's likely Region (Kraj). If > 1000 it's District/City.
            # Actually, Sreality API is distinct.
            # 10 = Praha (Kraj)
            # 5002 = Praha 2 (unknown type, likely district)
            
            if region_id == 10: # Praha Whole
                params["locality_region_id"] = 10
            elif region_id > 100: # Specific District
                 params["locality_district_id"] = region_id
            else:
                 params["locality_region_id"] = region_id
                 
        if min_price > 0 or max_price:
            # Sreality API v2 expects "min|max"
            # e.g. "0|5000000"
            low = min_price if min_price else 0
            high = max_price if max_price else "" # Empty means unlimited
            if not high: high = "" 
            
            params["czk_price_summary_order2"] = f"{low}|{high}"
            
        if layouts:
            # Layouts are bitmask in API? Or list? 
            # Param: category_sub_cb
            # Use | separator
            param_val = "|".join([str(l) for l in layouts])
            params["category_sub_cb"] = param_val

        results = []
        
        # Reverse map for link construction
        # ID -> Slug
        layout_id_map = {
            2: "1+kk", 3: "1+1",
            4: "2+kk", 5: "2+1",
            6: "3+kk", 7: "3+1",
            8: "4+kk", 9: "4+1",
            # Add others if needed
        }
        
        try:
            url = f"{self.BASE_URL}/cs/v2/estates"
            logger.info(f"API Request: {url} | Params: {params}")
            
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            
            data = resp.json()
            items = data.get("_embedded", {}).get("estates", [])
            
            logger.info(f"API returned {len(items)} items")
            
            for item in items:
                # Parse Item
                # name: "Prodej bytu 2+kk 55 m²"
                # locality: "Praha 2 - Vinohrady"
                # price: 8500000
                # hash_id: 2604741452
                
                title = item.get("name", "Unknown")
                loc = item.get("locality", "Unknown")
                price = item.get("price", 0)
                hash_id = item.get("hash_id")
                seo = item.get("seo", {})
                seo_loc = seo.get("locality")
                
                # Layout from response
                cat_sub = seo.get("category_sub_cb")
                layout_slug = layout_id_map.get(cat_sub, "byt") # Fallback to "byt" if unknown
                
                # Construct Link
                # Standard format: https://www.sreality.cz/detail/prodej/byt/[layout_slug]/[locality_slug]/[hash_id]
                if seo_loc:
                     link = f"https://www.sreality.cz/detail/prodej/byt/{layout_slug}/{seo_loc}/{hash_id}"
                else:
                     link = f"https://www.sreality.cz/detail/prodej/byt/unknown/unknown/{hash_id}"
                
                # Precise Parsing from Name
                # "Prodej bytu 2+kk 55 m²"
                import re
                
                # Area
                area = "0"
                area_match = re.search(r'(\d+)\s*m²', title)
                if area_match:
                    area = area_match.group(1)
                    
                # Layout
                # Extract "2+kk", "3+1"
                layout = title
                l_match = re.search(r'(\d+\+kk|\d+\+1|\d+\+0|1\+1|garsoniera)', title)
                if l_match:
                    layout = l_match.group(1)
                
                ad = RawPropertyAd(
                    source_url=link,
                    source_portal="sreality",
                    title=title,
                    price_raw=str(price),
                    location_raw=loc,
                    floor_area_raw=area, # Now cleanly "55"
                    layout=layout   
                )
                results.append(ad)
                
        except Exception as e:
            logger.error(f"API Error: {e}")
            
        return results
