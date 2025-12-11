import asyncio
import os
from loguru import logger
from src.harvester.models import RawPropertyAd
from src.cleaner.pipeline import DataCleaner
from src.cleaner.enrichment import Enricher
from src.reporting.analysis import FinancialAnalyst
from src.reporting.generator import ReportGenerator

async def main(input_limit: int = 3):
    logger.info("🚀 Starting RIA Agent Pipeline (MVP)...")
    
    # 1. HARVEST (Simulated for MVP speed, or real)
    # Using mock data to ensure "frontend" (Report) works immediately for user
    logger.info("Phase 1: Harvesting data...")
    raw_data = [
        RawPropertyAd(source_url="http://sreality.cz/detail/1", source_portal="sreality", title="Nice Flat", price_raw="7 500 000 Kč", floor_area_raw="55 m2", layout="2+kk"),
        RawPropertyAd(source_url="http://sreality.cz/detail/2", source_portal="sreality", title="Expensive One", price_raw="15 000 000 Kč", floor_area_raw="120 m2", layout="4+1"),
        RawPropertyAd(source_url="http://sreality.cz/detail/3", source_portal="sreality", title="Cheap Fixer", price_raw="3 500 000 Kč", floor_area_raw="40 m2", layout="1+1"),
    ]
    
    # 2. CLEAN & ENRICH
    logger.info("Phase 2: Cleaning & Enriching...")
    cleaner = DataCleaner()
    enricher = Enricher()
    analyst = FinancialAnalyst(min_yield_target=4.5)
    
    final_results = []
    
    for raw in raw_data:
        # Pipeline execution
        clean = cleaner.process_ad(raw)
        enriched = await enricher.enrich_location(clean)
        
        # 3. ANALYZE
        metrics = analyst.evaluate(enriched)
        
        final_results.append((enriched, metrics))
        
    # 4. REPORT
    logger.info("Phase 3: Generating Investment Memorandum...")
    report_md = ReportGenerator.generate_markdown(final_results)
    
    # Output
    output_path = "investment_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    logger.success(f"✅ Report generated: {os.path.abspath(output_path)}")
    print("\n" + "="*50)
    print(report_md)
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
