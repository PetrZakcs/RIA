import sys
import os

# Bridge for Vercel Serverless Function
# Vercel looks for api/index.py or similar.
# We need to make sure 'src' is importable.

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the FastAPI app
try:
    from src.api.app import app
except ImportError as e:
    # Safe Mode Fallback for Import Errors at Entrypoint level
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    import traceback
    
    app = FastAPI()
    error_msg = traceback.format_exc()
    
    @app.get("/{catchall:path}")
    def error_handler(catchall: str):
        return HTMLResponse(f"""
        <html><body>
            <h1 style='color:red'>Entrypoint Import Error</h1>
            <pre>{error_msg}</pre>
            <p>Sys Path: {sys.path}</p>
        </body></html>
        """, status_code=500)
