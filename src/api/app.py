import sys
import os
import asyncio
import traceback

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
from loguru import logger

# --- 1. CONFIGURATION & PATHS ---
# Vercel: Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR)) # src/api -> src -> root
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Windows asyncio fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- 2. INITIALIZE APP EARLY ---
app = FastAPI(title="RIA - Real Estate Investment Agent")

# Mount static files (with safety check)
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Templates
templates_dir = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)

# --- 3. SAFE IMPORT LOADING ---
IMPORT_ERROR = None

try:
    from src.harvester.api_engine import SrealityApiEngine
    from src.common.config import settings
    from src.harvester.models import RawPropertyAd
    from src.cleaner.pipeline import DataCleaner
    from src.cleaner.enrichment import Enricher
    from src.reporting.analysis import FinancialAnalyst
    from src.reporting.generator import ReportGenerator
    
    logger.info("Modules imported successfully.")
    
except Exception as e:
    IMPORT_ERROR = traceback.format_exc()
    logger.error(f"Failed to import modules: {IMPORT_ERROR}")


# --- 4. ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # IF IMPORTS FAILED, SHOW ERROR ON HOMEPAGE
    if IMPORT_ERROR:
        return f"""
        <html>
            <body style="font-family: monospace; background: #eee; padding: 20px;">
                <h1 style="color: red;">Startup Failed (Safe Mode)</h1>
                <p>The application could not load core modules.</p>
                <h3>Traceback:</h3>
                <pre style="background: #fff; padding: 10px; border: 1px solid #999;">{IMPORT_ERROR}</pre>
                <h3>Sys Path:</h3>
                <pre>{sys.path}</pre>
                <h3>CWD:</h3>
                <pre>{os.getcwd()}</pre>
            </body>
        </html>
        """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, prompt: str = Form(...)):
    if IMPORT_ERROR:
        return HTMLResponse(f"<h1>Startup Error</h1><pre>{IMPORT_ERROR}</pre>", status_code=500)
        
    results = []
    
    # 1. Location Parsing Logic (Mapped to IDs for API)
    import unicodedata
    def slugify(text: str) -> str:
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        return text.lower().replace(" ", "-")
    
    clean_prompt = prompt.lower()
    prompt_slug = slugify(prompt)
    
    region_id = None
    
    # Map: City -> ID
    known_locations = {
        "praha": 10, 
        "brno": 3702, 
        "ostrava": 3807, 
        "plzen": 3407, 
        "olomouc": 3805
    }
    
    # Simple Parsing (Copied from original)
    import re
    p_match = re.search(r'praha\s*(\d+)', clean_prompt)
    if p_match:
        dist_num = int(p_match.group(1))
        if 1 <= dist_num <= 10:
             region_id = 5000 + dist_num
    
    if not region_id:
        for city, r_id in known_locations.items():
            if city in prompt_slug:
                region_id = r_id
                break
    
    if not region_id:
        region_id = 10 

    # Parsing Filters
    price_max = None
    layouts = []
    
    price_match = re.search(r'(?:do|max)(\d+(?:mil|m)?)', clean_prompt.replace(" ", ""))
    if price_match:
        val_str = price_match.group(1)
        if "mil" in val_str or "m" in val_str:
            base = float(re.sub(r'[a-z]', '', val_str))
            price_max = int(base * 1_000_000)
        else:
            price_max = int(val_str)
            
    layout_map = {
        "1kk": 2, "1+kk": 2, "11": 3, "1+1": 3,
        "2kk": 4, "2+kk": 4, "21": 5, "2+1": 5,
        "3kk": 6, "3+kk": 6, "31": 7, "3+1": 7,
        "4kk": 8, "4+kk": 8, "41": 9, "4+1": 9
    }
    
    norm_prompt = clean_prompt.replace(" ", "").replace(",", "")
    for key, val in layout_map.items():
        if key in norm_prompt:
            layouts.append(val)
            
    logger.info(f"User Prompt: '{prompt}' -> RegionID: {region_id} | MaxPrice: {price_max} | Layouts: {layouts}")

    # Execution
    engine = SrealityApiEngine()
    
    try:
        raw_data = await engine.search_apartments(
            region_id=region_id,
            max_price=price_max,
            layouts=layouts
        )
        
        cleaner = DataCleaner()
        enricher = Enricher()
        analyst = FinancialAnalyst(min_yield_target=4.0)
        
        for raw in raw_data:
            clean = cleaner.process_ad(raw)
            enriched = await enricher.enrich_location(clean)
            metrics = analyst.evaluate(enriched)
            results.append({"ad": enriched, "metrics": metrics})
    
    except Exception as e:
        logger.exception("Error during API pipeline execution")
        # Fail gracefully
        results = []
    finally:
        await engine.close()
        
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
