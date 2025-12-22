import sys
import os
import asyncio
import traceback

from fastapi import FastAPI, Request, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
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

# Imports for DB & Auth
# WRAPPED IN TRY/EXCEPT FOR VERCEL DEBUGGING
DB_ERROR = None
try:
    from src.database.session import engine, Base
    # Create Tables
    # This might fail if DB Connection is bad (Timeout, Password)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")
except Exception as e:
    DB_ERROR = traceback.format_exc()
    logger.error(f"Database Startup Error: {DB_ERROR}")
    # We continue, so Vercel doesn't crash immediately. 
    # Routes relying on DB will fail, but Home will show error.


# Core Logic imports
from src.harvester.api_engine import SrealityApiEngine
# from src.cleaner.text_processor import normalize_prompt # Unused/Missing
from src.reporting.analysis import FinancialAnalyst

try:
    from src.reporting.generator import generate_report_md
except ImportError:
    generate_report_md = None

app = FastAPI(title="RIA - Real Estate Investment Agent")
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
         return HTMLResponse(f"<h1>Startup Import Error</h1><pre>{IMPORT_ERROR}</pre>", status_code=500)
    
    # IF DATABASE FAILED
    if 'DB_ERROR' in globals() and DB_ERROR:
         return HTMLResponse(f"<h1>Database Connection Error</h1><p>Failed to connect to Supabase.</p><pre>{DB_ERROR}</pre>", status_code=500)

    return templates.TemplateResponse("index.html", {"request": request})




@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# AI Analysis Endpoint
from pydantic import BaseModel
class AnalyzeRequest(BaseModel):
    hash_id: int
    title: str
    price: float
    yield_pct: float

@app.post("/api/analyze")
async def analyze_property_endpoint(data: AnalyzeRequest, request: Request):
    # Security: Check Valid Session/Token (Enterprise only?)
    # For MVP: Allow all logged in users (or even public for demo if needed)
    # Ideally check jwt tier in cookie.
    
    from src.harvester.api_engine import SrealityApiEngine
    from src.ai.service import ai_service
    
    engine = SrealityApiEngine()
    try:
        # 1. Fetch Description
        description = await engine.get_listing_detail(data.hash_id)
        if not description:
            description = "Popis se nepodařilo načíst."
            
        # 2. Analyze
        analysis = ai_service.analyze_property(
            title=data.title, 
            description=description, 
            price=data.price, 
            yield_pct=data.yield_pct
        )
        
        return analysis.dict()
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"error": str(e)}
    finally:
        await engine.close()
from fastapi import BackgroundTasks

@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, background_tasks: BackgroundTasks, prompt: str = Form(...)):
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
    
    # Map: Regions and Common Cities to Sreality Region IDs
    # Format: "name": (ID, Type) where Type is 'region' or 'district'
    # For backwards compatibility, plain integers are treated as 'region' (or heuristic)
    known_locations = {
        # Whole Country
        "ceska republika": (-99, 'region'), "cr": (-99, 'region'), "cz": (-99, 'region'),
        
        # Major Cities (Districts) - Precise Search
        # Praha & Brno are special/known
        "praha": (10, 'region'), "praze": (10, 'region'), # Praha is unique (Region 10 = Capital)
        "brno": (72, 'district'), "brne": (72, 'district'),

        # Regions (Kraje) - ONLY map explicit Region names, NOT cities
        "jihocesky": (1, 'region'), 
        "plzensky": (2, 'region'),
        "karlovarsky": (3, 'region'),
        "ustecky": (4, 'region'),
        "liberecky": (5, 'region'),
        "kralovehradecky": (6, 'region'),
        "pardubicky": (7, 'region'),
        "olomoucky": (8, 'region'),
        "zlinsky": (9, 'region'),
        "stredocesky": (11, 'region'),
        "moravskoslezsky": (12, 'region'),
        "vysocina": (13, 'region'),
        "jihomoravsky": (14, 'region'),

        # Note: We REMOVED "ostrava", "plzen", "liberec", etc. from here.
        # Why? Because mapping "ostrava" -> Region 12 (Moravskoslezsky) caused searching the WHOLE region.
        # Now, "ostrava" will fall through to fuzzy/text search, setting region_text="ostrava",
        # which Sreality API handles by searching just Ostrava (Correct).
    }


    
    # 1. Check for Specific Prague Districts first (Praha 1-10)
    import re
    p_match = re.search(r'praha\s*(\d+)', clean_prompt)
    if p_match:
        dist_num = int(p_match.group(1))
        if 1 <= dist_num <= 10:
             region_id = 5000 + dist_num
    
    region_type = None # Default
    
    # Execution

         
    # Execution
    
    # --- RESTORED LOGIC START ---
    
    # 3. Municipality Normalization (Simplified)
    # If no Region ID found yet, try to match a name from our DB
    import json
    target_location_filter = None
    
    try:
        json_path = os.path.join(os.path.dirname(BASE_DIR), "common", "cz_municipalities.json")
        
        if os.path.exists(json_path) and not region_id:
             with open(json_path, "r", encoding="utf-8") as f:
                  muni_data = json.load(f)
             
             munis = muni_data.get("municipalities", [])
             
             stop_words_loc = set(["byt", "dum", "v", "na", "u", "prodej", "pronajem", "okres", "kraj", "do", "cena"])
             user_words = [w for w in clean_prompt.split() if w not in stop_words_loc and len(w)>2]
             
             import difflib
             logger.info(f"Fuzzy Match Debug - User Words: {user_words}") 
             
             for w in user_words:
                 if w.lower() in ["praha", "praze", "brno", "brne", "ostrava", "ostrave"]:
                     continue 
                 
                 names = [m['hezkyNazev'] for m in munis]
                 matches = difflib.get_close_matches(w.capitalize(), names, n=1, cutoff=0.85)
                 
                 logger.info(f"Checking word '{w}' -> Matches: {matches}")

                 if matches:
                     match_name = matches[0]
                     target_location_filter = match_name
                     logger.info(f"Set target_location_filter to: {target_location_filter}")
                     break
                     
    except Exception as e:
        logger.error(f"Failed to load municipalities: {e}")

    # 4. Parsing Property Type
    category_main = 1 
    type_keywords = {
        "dum": 2, "dům": 2, "domu": 2, "vila": 2, "chalupa": 2, "barak": 2,
        "pozemek": 3, "pozemky": 3, "zahrada": 3, "les": 3, "pole": 3,
        "chata": 4, "rekreace": 4, "chalupu": 2, 
        "komerce": 5, "kancelar": 5, "obchod": 5, "sklad": 5
    }
    
    for word in clean_prompt.split():
        w = word.strip(",.")
        if w in type_keywords:
            category_main = type_keywords[w]
            break

    # 5. Parsing Filters (Price & Layouts)
    price_max = None
    layouts = []
    
    import re
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

    # 6. Universal Search Check
    if region_id is None and region_type is None and target_location_filter is None:
         # Universal Fallback - Try to find text fallback if not explicit
        stop_words = ["byt", "dum", "prodej", "pronajem", "kk", "1+1", "2+kk", "3+kk", "1+kk", "do", "mil", "milion", "czk", "kc", "v", "ve", "na", ",", "cr", "cz", "ceske", "republice", "republika"]
        words = clean_prompt.split()
        potential_locs = [
            w for w in words 
            if w.strip() not in stop_words 
            and not w[0].isdigit() 
            and len(w) > 2
        ]
        
        if potential_locs:
            target_location_filter = " ".join(potential_locs)
    # --- RESTORED LOGIC END ---
    
    engine = SrealityApiEngine()

    
    try:
        # Use Native Search
        raw_data = await engine.search_apartments(
            region_id=region_id,
            region_type=region_type,
            max_price=price_max,
            layouts=layouts,
            region_text=target_location_filter,
            category_main=category_main
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
        
    # Ingest Data in Background
    if results:
         # Need valid RawPropertyAd list. 'raw_data' is it.
         # Session Handling: BackgroundTasks runs after response, so dependency injection of DB might be tricky if not careful.
         # But we can instantiate a new session in the wrapper function.
         
         from src.database.session import SessionLocal
         from src.harvester.ingestion import IngestionService
         
         def background_ingest(ads):
             db = SessionLocal()
             try:
                 svc = IngestionService(db)
                 svc.process_batch(ads)
             except Exception as e:
                 logger.error(f"Background Ingestion Failed: {e}")
             finally:
                 db.close()
         
         background_tasks.add_task(background_ingest, raw_data)

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
