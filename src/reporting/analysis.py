from pydantic import BaseModel
from src.cleaner.models import CleanPropertyAd

class FinancialMetrics(BaseModel):
    gross_yield_percent: float = 0.0
    estimated_annual_rent_czk: float = 0.0
    monthly_rent_per_m2: float = 0.0 # From Market Data
    market_sale_per_m2: float = 0.0  # From Market Data
    undervaluation_percent: float = 0.0 # Positive = Good deal
    is_good_deal: bool = False



import json
import os
from src.cleaner.models import CleanPropertyAd

# Load Market Map Global
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, "common", "market_data.json")

MARKET_MAP = {}
try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        MARKET_MAP = json.load(f)
except Exception as e:
    print(f"Stats Load Error: {e}")

class FinancialAnalyst:
    def __init__(self, min_yield_target: float = 4.0):
        self.min_yield_target = min_yield_target

    def get_market_data(self, locality: str) -> dict:
        default = MARKET_MAP.get("default", {"rent": 200, "sale": 60000})
        
        if not locality:
            return default
            
        loc_lower = locality.lower()
        
        # 1. Check Cities
        for city, data in MARKET_MAP.get("cities", {}).items():
            if city in loc_lower:
                return data
                
        # 2. Check Regions
        for region, data in MARKET_MAP.get("regions", {}).items():
            if region.lower() in loc_lower:
                return data
        
        return default

    def evaluate(self, ad: CleanPropertyAd) -> FinancialMetrics:
        # 1. Market Data Lookup
        market_stats = self.get_market_data(ad.locality or "")
        market_rent_per_m2 = market_stats.get("rent", 200)
        market_sale_per_m2 = market_stats.get("sale", 60000)
        
        monthly_rent = ad.floor_area_m2 * market_rent_per_m2 if ad.floor_area_m2 else 0
        annual_rent = monthly_rent * 12

        
        # 2. Yield Calculation
        gross_yield = 0.0
        # Sanity Check: Price must be > 100k to be real (avoids 'Price on Request' = 1 CZK issues)
        if ad.price_czk and ad.price_czk > 100000:
            gross_yield = (annual_rent / ad.price_czk) * 100
            
        # 3. Decision
        is_good = gross_yield >= self.min_yield_target
        
        # 4. Undervaluation (Market Diff)
        undervaluation = 0.0
        if ad.price_per_m2 and ad.price_per_m2 > 1000 and market_sale_per_m2:
            # (Market - Actual) / Market
            # 100k - 80k / 100k = 20% undervalued
            diff = market_sale_per_m2 - ad.price_per_m2
            undervaluation = (diff / market_sale_per_m2) * 100

        
        return FinancialMetrics(
            gross_yield_percent=round(gross_yield, 2),
            estimated_annual_rent_czk=round(annual_rent, 0),
            price_per_m2=ad.price_per_m2 or 0,
            monthly_rent_per_m2=market_rent_per_m2, 
            market_sale_per_m2=market_sale_per_m2,
            undervaluation_percent=round(undervaluation, 1),
            is_good_deal=is_good
        )


