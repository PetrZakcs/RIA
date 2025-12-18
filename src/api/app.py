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
from src.database.session import engine, Base
from src.api.routes import auth
# Create Tables
Base.metadata.create_all(bind=engine)

# Core Logic imports
from src.harvester.api_engine import SrealityApiEngine
# from src.cleaner.text_processor import normalize_prompt # Unused/Missing
from src.reporting.analysis import FinancialAnalyst

try:
    from src.reporting.generator import generate_report_md
except ImportError:
    generate_report_md = None

app = FastAPI(title="RIA - Real Estate Investment Agent")
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

from src.api.routes import payment
app.include_router(payment.router, prefix="/payment", tags=["Payment"])



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
        # ... (error handling preserved in simple return if needed, unlikely here since imported)
        pass 
    if IMPORT_ERROR:
         return HTMLResponse(f"<h1>Startup Error</h1><pre>{IMPORT_ERROR}</pre>", status_code=500)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    from src.common.config import settings
    return templates.TemplateResponse("register.html", {
        "request": request,
        "stripe_pk": settings.STRIPE_PUBLISHABLE_KEY,
        "prices": {
            "basic": settings.STRIPE_PRICE_BASIC,
            "business": settings.STRIPE_PRICE_BUSINESS,
            "enterprise": settings.STRIPE_PRICE_ENTERPRISE
        }
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

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
    
    # ---------------- Feature Gating ----------------
    from fastapi import Cookie
    from jose import jwt, JWTError
    from src.auth.security import SECRET_KEY, ALGORITHM
    
    # Defaults
    user_tier = "BASIC"
    
    # Decode Cookie
    # Note: We access cookie manually or via Depends. Here manually via Request if simpler, 
    # but let's use the Cookie parameter approach which is cleaner but requires function signature change.
    # Changing function signature in the middle of this big function might be messy with REPLACE.
    # Let's inspect cookies from `request` object directly.
    
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_tier = payload.get("tier", "BASIC")
        except JWTError:
            pass # Invalid token -> treat as BASIC/Guest
            
    # ENFORCEMENT
    # Rule: BASIC cannot search "Whole CZ" (region_id is None)
    # Exception: "Ceska Republika" explicitly asked (-99) is also blocked.
    # Actually, logic below: 'if not region_id' implies Universall Search.
    
    # We need to perform this check AFTER region_id is resolved or confirmed missing.
    # The logic continues below...

    
    # 2. Check General Location Map
    # Priority: Check longest matches first to avoid "Praha" catching "Praha-vychod"
    if not region_id:
        # Sort keys by length desc
        sorted_locs = sorted(known_locations.items(), key=lambda x: len(x[0]), reverse=True)
        
        for city, val in sorted_locs:
            if city in prompt_slug:
                # Handle Tuple vs Int
                if isinstance(val, tuple):
                    r_id, r_type = val
                else:
                    r_id, r_type = val, 'region'
                
                if r_id == -99:
                    region_id = None # Explicitly Whole CR
                    # Ensure we pass the TYPE so we know to trigger universal logic if needed
                    # Actually universal logic triggers on (region_id is None and region_type is None)
                    # BUT here we might have region_type='district'.
                    # We need to signal Universal Search.
                    # Let's keep region_type as None for Universal trigger?
                    # Or update Universal trigger to check for r_id == -99 flag?
                    # Code below checks: `if region_id is None and region_type is None:`
                    # So if we set region_type = 'district', Universal logic SKIPS!
                    # FIX: If r_id is -99, we should FORCE region_type to None or handle it.
                    region_type = None
                else:
                    region_id = r_id
                    region_type = r_type
                break
    
    # NEW 3. Municipality Normalization (from JSON)
    # If no Region ID found yet, try to match a name from our DB
    import json
    
    # Cache variable for module scope? 
    # For now, just load safely. 
    try:
        json_path = os.path.join(BASE_DIR, "src", "common", "cz_municipalities.json")
        # Correction: BASE_DIR is src/api, so ../common -> src/common? 
        # Check path: c:\Users\Admin\Desktop\ria\src\api\app.py -> BASE_DIR
        # PROJECT_ROOT is c:\Users\Admin\Desktop\ria\src (actually src/api -> src -> root?? No)
        # Let's use relative path carefully.
        # BASE_DIR = .../src/api
        # Target: .../src/common/cz_municipalities.json
        json_path = os.path.join(os.path.dirname(BASE_DIR), "common", "cz_municipalities.json")
        
        if os.path.exists(json_path) and not region_id:
             with open(json_path, "r", encoding="utf-8") as f:
                  muni_data = json.load(f)
             
             munis = muni_data.get("municipalities", [])
             
             # Smart Search:
             # Look for words in clean_prompt that match a municipality name.
             # clean_prompt words: ["byt", "v", "krnově"]
             
             best_match = None
             max_score = 0
             
             # Create simple specialized dictionary for speed? 
             # Or just brute force (6000 items is fast for python).
             
             stop_words_loc = set(["byt", "dum", "v", "na", "u", "prodej", "pronajem", "okres", "kraj", "do", "cena"])
             user_words = [w for w in clean_prompt.split() if w not in stop_words_loc and len(w)>2]
             
             # We want to match "krnově" -> "Krnov"
             # Simple startswith check might work for locative? "Krnov" in "Krnově" -> True
             # "Praze" -> "Praha" (False). "Brně" -> "Brno" (False).
             # So we ideally need fuzzy match.
             # Difflib?
             import difflib
             
             for w in user_words:
                 # Check exact candidates first?
                 # difflib.get_close_matches is good.
                 
                 # Optimization: specific check for Praha/Brno/Ostrava to avoid silly matches
                 if w.lower() in ["praha", "praze", "brno", "brne", "ostrava", "ostrave"]:
                     continue # Handled by known_locations
                 
                 names = [m['hezkyNazev'] for m in munis]
                 matches = difflib.get_close_matches(w.capitalize(), names, n=1, cutoff=0.85)
                 
                 if matches:
                     match_name = matches[0]
                     
                     # Fix for Brandys and others with dash nuances
                     # DB: "Brandýs nad Labem – Stará Boleslav" (Spaced En-dash)
                     # Sreality might prefer simple hyphen or just "Brandýs nad Labem"
                     # Testing needed? Sreality usually accepts the official name.
                     
                     logger.info(f"Fuzzy parsing: '{w}' -> '{match_name}'")
                     target_location_filter = match_name
                     logger.info(f"Location Normalized: {target_location_filter}")
                     # Trigger Native Search with this Clean Name
                     break
                     
    except Exception as e:
        logger.error(f"Failed to load municipalities: {e}")

    # 4. Default Fallback (if still nothing)
                     
    except Exception as e:
        logger.error(f"Failed to load municipalities: {e}")

    # 4. Default Fallback (if still nothing)

    # New logic: If user says something vague, maybe default to Whole CR?
    # BUT: Safety first. If they typed garbage, showing Whole CR results is better than just Prague
    # because they might have typed a small town name we don't know, and getting 0 results for CZ is correct logic,
    # whereas getting Prague results is confusing.
    # However, for now, let's Stick to None (Whole CR) if nothing found.
    # Actually, keep logic explicit.
    
    if not region_id and region_id is not None:
         # If it's still specifically False/None but NOT because we set it to None explicitly (via -99)
         # We check if we actually found something.
         # The 'region_id' is initialized to None.
         # If we didn't find a match, it stays None.
         # So we want to treat "No Match" -> "Whole Country" ?
         # OR "No Match" -> "Praha"?
         # Let's keep it None (Whole Country) as intended.
         pass
         
 

    # Parsing Property Type (Houses, Land, etc.)
    # Defaults to Apartments (1)
    category_main = 1 
    
    type_keywords = {
        "dum": 2, "dům": 2, "domu": 2, "vila": 2, "chalupa": 2, "barak": 2,
        "pozemek": 3, "pozemky": 3, "zahrada": 3, "les": 3, "pole": 3,
        "chata": 4, "rekreace": 4, "chalupu": 2, # Chalupa is often house or recreation, usually 2 structure on sreality
        "komerce": 5, "kancelar": 5, "obchod": 5, "sklad": 5
    }
    
    for word in clean_prompt.split():
        # Strip punctuation
        w = word.strip(",.")
        if w in type_keywords:
            category_main = type_keywords[w]
            break # Priority to first match
            
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
            
    logger.info(f"User Prompt: '{prompt}' -> RegionID: {region_id} (Type: {region_type}) | MaxPrice: {price_max} | Layouts: {layouts}")

    # Universal Search Fallback Logic
    target_location_filter = None
    is_universal_search = False
    
    if region_id is None and region_type is None:
        # Determine if this is a precise village search or generic "Byt na prodej"
        stop_words = ["byt", "dum", "prodej", "pronajem", "kk", "1+1", "2+kk", "3+kk", "1+kk", "do", "mil", "milion", "czk", "kc", "v", "ve", "na", ","]
        words = clean_prompt.split()
        potential_locs = [
            w for w in words 
            if w.strip() not in stop_words 
            and not w[0].isdigit() 
            and len(w) > 2
        ]
        
        if potential_locs:
            target_location_filter = " ".join(potential_locs)
            logger.info(f"Unknown Location Detected. Using Native Text Search for: '{target_location_filter}'")
        else:
            is_universal_search = True

    # ---- BLOCKING LOGIC ----
    # Basic Users cannot do Universal ("Whole CZ") or fuzzy matches that Scan whole CZ
    # We allow "target_location_filter" because that implies a specific intent (even if region ID failed)
    # BUT if target_location_filter is also None -> It's truly "Whole CZ".
    
    if user_tier == "BASIC" and is_universal_search:
         return HTMLResponse("""
            <html>
            <head><link rel="stylesheet" href="/static/style.css"></head>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;background:#f8f9fa;">
                <div class="card" style="padding:2rem;text-align:center;max-width:500px;">
                    <h1 style="color:var(--primary-color)">Je vyžadován Upgrade 🔒</h1>
                    <p>Skenování celé ČR je prémiová funkce.</p>
                    <p>Váš tarif <b>BASIC</b> umožňuje prohledávat pouze konkrétní lokality (např. "Praha", "Brno").</p>
                    <div style="margin-top:1.5rem">
                         <a href="/" class="btn-secondary">Zkusit "Praha"</a>
                         <a href="/register" class="btn-primary">Upgradovat na Business</a>
                    </div>
                </div>
            </body>
            </html>
         """)

         
    # Execution
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
