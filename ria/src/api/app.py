from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
from loguru import logger
from typing import List
import asyncio
import sys

# Windows asyncio fix for Playwright/Subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Import existing core logic
# Import API Engine
from src.harvester.api_engine import SrealityApiEngine
from src.common.config import settings

from src.harvester.models import RawPropertyAd
from src.cleaner.pipeline import DataCleaner
from src.cleaner.enrichment import Enricher
from src.reporting.analysis import FinancialAnalyst
from src.reporting.generator import ReportGenerator

app = FastAPI(title="RIA - Real Estate Investment Agent")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/api/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, prompt: str = Form(...)):
    results = []
    
    # 1. Location Parsing Logic (Mapped to IDs for API)
    import unicodedata
    def slugify(text: str) -> str:
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        return text.lower().replace(" ", "-")

    # Map: City -> ID
    # 10 = Praha (Kraj)
    # 5001-5010 = Praha 1-10
    # Brno = 3702 (Okres Brno-mesto)
    # Ostrava = 3807 (Okres Ostrava-mesto)
    known_locations = {
        "praha": 10, 
        "brno": 3702, 
        "ostrava": 3807, 
        "plzen": 3407, # Okres Plzen-mesto
        "olomouc": 3805 # Okres Olomouc
    }

    clean_prompt = prompt.lower()
    prompt_slug = slugify(prompt)
    
    region_id = None
    
    # Specific Praha 1-10 check
    import re
    p_match = re.search(r'praha\s*(\d+)', clean_prompt)
    if p_match:
        dist_num = int(p_match.group(1))
        if 1 <= dist_num <= 10:
             # Heuristic: 5000 + num often works for API (legacy IDs)
             # Actually, simpler is to just generic search or use known exacts.
             # Sreality API IDs for P1-P10 are roughly:
             # P1:5001, P2:5002, ... P10:5010
             region_id = 5000 + dist_num
    
    if not region_id:
        for city, r_id in known_locations.items():
            if city in prompt_slug:
                region_id = r_id
                break
    
    # Default to Praha if unknown (MVP)
    if not region_id:
        region_id = 10 

    # 2. Parsing Filters (Price & Layout)
    price_max = None
    layouts = []
    
    # Price
    price_match = re.search(r'(?:do|max)(\d+(?:mil|m)?)', clean_prompt.replace(" ", ""))
    if price_match:
        val_str = price_match.group(1)
        if "mil" in val_str or "m" in val_str:
            base = float(re.sub(r'[a-z]', '', val_str))
            price_max = int(base * 1_000_000)
        else:
            price_max = int(val_str)
            
    # Layouts (Map to Integers 1+kk=2 etc)
    layout_map = {
        "1kk": 2, "1+kk": 2,
        "11": 3, "1+1": 3,
        "2kk": 4, "2+kk": 4,
        "21": 5, "2+1": 5,
        "3kk": 6, "3+kk": 6,
        "31": 7, "3+1": 7,
        "4kk": 8, "4+kk": 8,
        "41": 9, "4+1": 9
    }
    
    norm_prompt = clean_prompt.replace(" ", "").replace(",", "")
    for key, val in layout_map.items():
        if key in norm_prompt:
            layouts.append(val)
            
    logger.info(f"User Prompt: '{prompt}' -> RegionID: {region_id} | MaxPrice: {price_max} | Layouts: {layouts}")

    # 3. Execution via API Engine
    engine = SrealityApiEngine()
    
    try:
        raw_data = await engine.search_apartments(
            region_id=region_id,
            max_price=price_max,
            layouts=layouts
        )
        
        if not raw_data:
            logger.warning("No data found via API.")
            
        cleaner = DataCleaner()
        enricher = Enricher()
        analyst = FinancialAnalyst(min_yield_target=4.0)
        
        for raw in raw_data:
            clean = cleaner.process_ad(raw)
            enriched = await enricher.enrich_location(clean)
            metrics = analyst.evaluate(enriched)
            results.append({"ad": enriched, "metrics": metrics})
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.exception("Error during API pipeline execution")
        # return HTMLResponse(content=f"<h1>Error processing request</h1><pre>{error_trace}</pre>", status_code=500)
        # Fail gracefully
        results = []
    finally:
        await engine.close()
        
    # Sort
    results.sort(key=lambda x: x["metrics"].gross_yield_percent, reverse=True)
    
    return templates.TemplateResponse("results.html", {
        "request": request, 
        "results": results, 
        "prompt": prompt
    })
        
    # Sort
    results.sort(key=lambda x: x["metrics"].gross_yield_percent, reverse=True)
    
    return templates.TemplateResponse("results.html", {
        "request": request, 
        "results": results, 
        "prompt": prompt
    })

def start_server():
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    start_server()
