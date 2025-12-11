import asyncio
from playwright.async_api import async_playwright, Page, Browser
from loguru import logger
from typing import List, Optional
from src.common.config import settings
from src.harvester.models import RawPropertyAd

class PlaywrightEngine:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-position=-2400,-2400" 
            ]
        )
        logger.info("Playwright engine started.")

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright engine stopped.")

    async def scrape_detail(self, url: str) -> Optional[RawPropertyAd]:
        """
        Scrapes a single detail page.
        """
        if not self.browser:
            raise RuntimeError("Browser not started")
            
        page = await self.browser.new_page()
        try:
            logger.info(f"Navigating to {url}")
            await page.goto(url, timeout=30000)
            
            # Sreality specific selectors (simplified for MVP)
            # In production this needs robust selector management
            title = await page.title()
            
            # Attempt to extract price
            price_raw = "N/A"
            try:
                # Common selector for Sreality detail price
                price_el = await page.query_selector(".norm-price")
                if price_el:
                    price_raw = await price_el.inner_text()
            except:
                pass

            raw_ad = RawPropertyAd(
                source_url=url,
                source_portal="sreality",
                title=title,
                price_raw=price_raw,
                description="Scraped real data"
            )
            return raw_ad
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None
        finally:
            await page.close()

    async def scrape_search_results(self, search_url: str, limit: int = 5) -> List[RawPropertyAd]:
        """
        Scrapes a list of properties from a search result page.
        """
        if not self.browser:
            raise RuntimeError("Browser not started")
            
        # Use a real User-Agent to avoid "HeadlessChrome" detection
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        # Stealth: Hide webdriver property
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        results = []
        try:
            logger.info(f"Searching: {search_url}")
            await page.goto(search_url, timeout=30000)
            
            # 1. Handle Cookie Consent
            try:
                consent_button = await page.query_selector("button.szn-cmp-dialog-container__button--primary")
                if consent_button:
                    logger.info("Found cookie consent. Clicking...")
                    await consent_button.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"Cookie warning logic check failed: {e}")

            # 2. Wait for content
            try:
                # Wait longer for headless
                await page.wait_for_selector(".property, .dir-property-list", timeout=20000)
            except:
                logger.error("Content did not load in time. Saving debug_timeout.png")
                await page.screenshot(path="src/api/static/debug_timeout.png")
                return []
            
            # Select property cards
            cards = await page.query_selector_all(".property")
            if not cards:
                 cards = await page.query_selector_all(".dir-property-list > div")

            logger.info(f"Found {len(cards)} card elements")
            
            if not cards:
                logger.warning("No cards found on page. Saving debug_empty.png")
                await page.screenshot(path="src/api/static/debug_empty.png")
            
            for i, card in enumerate(cards):
                if i >= limit:
                    break
                    
                # Extract basic info from card
                try:
                    title_el = await card.query_selector("span.name")
                    if not title_el: title_el = await card.query_selector(".name")
                    title = await title_el.inner_text() if title_el else "Unknown"
                    
                    price_el = await card.query_selector(".norm-price")
                    price = await price_el.inner_text() if price_el else "0"
                    
                    # Link
                    link_el = await card.query_selector("a.title") 
                    if not link_el: link_el = await card.query_selector("a")
                        
                    href = await link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = "https://www.sreality.cz" + href
                        
                    loc_el = await card.query_selector(".locality")
                    location = await loc_el.inner_text() if loc_el else ""
                    
                    logger.info(f"Parsed: {title} | {price}")
                    
                    # Create Raw object
                    ad = RawPropertyAd(
                        source_url=href,
                        source_portal="sreality",
                        title=title,
                        price_raw=price,
                        location_raw=location,
                        floor_area_raw=title, 
                        layout=title          
                    )
                    results.append(ad)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse card: {e}")
                    continue
                    
            return results
        except Exception as e:
            logger.error(f"Search failed processing: {e}")
            return []
        finally:
            await page.close()

if __name__ == "__main__":
    # Quick test
    async def test():
        engine = PlaywrightEngine(headless=False)
        await engine.start()
        # await engine.scrape_detail("https://example.com")
        await engine.stop()
    
    asyncio.run(test())
