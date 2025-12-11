import asyncio
from loguru import logger
from src.harvester.engine import PlaywrightEngine
from src.common.config import settings

async def run_harvester(urls: list[str]):
    logger.info("Starting Agent A: Data Harvester")
    
    engine = PlaywrightEngine(headless=settings.HEADLESS)
    await engine.start()
    
    try:
        results = []
        for url in urls:
            data = await engine.scrape_detail(url)
            if data:
                results.append(data)
                logger.success(f"Successfully scraped: {data.title}")
                # TODO: Save to MongoDB
                
        logger.info(f"Harvesting finished. Collected {len(results)} items.")
        return results
        
    finally:
        await engine.stop()

if __name__ == "__main__":
    # Example usage
    target_urls = [
        "https://www.sreality.cz", # Example target
    ]
    asyncio.run(run_harvester(target_urls))
