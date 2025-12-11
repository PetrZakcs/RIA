import sys
import asyncio
import uvicorn

def main():
    # CRITICAL FIX for Windows + Playwright
    # Forces Python to use ProactorEventLoop which supports subprocesses (needed for browser)
    # This must be set before ANY async loop is created.
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Run Uvicorn programmatically
    # We disable 'reload' to ensure we stay in this process with the correct loop policy
    print("🚀 Starting RIA Server on http://127.0.0.1:8000")
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, reload=False, loop="asyncio")

if __name__ == "__main__":
    main()
