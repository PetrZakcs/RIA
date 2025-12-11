from pydantic import BaseModel
from src.cleaner.models import CleanPropertyAd

class FinancialMetrics(BaseModel):
    gross_yield_percent: float = 0.0
    estimated_annual_rent_czk: float = 0.0
    price_per_m2: float = 0.0
    is_good_deal: bool = False

class FinancialAnalyst:
    def __init__(self, min_yield_target: float = 4.0):
        self.min_yield_target = min_yield_target

    def evaluate(self, ad: CleanPropertyAd) -> FinancialMetrics:
        # 1. Estimation of Rent (Mock model)
        # In Beta/V1 this would come from Agent C (ML Model)
        # Here we use a heuristic: 300 CZK/m2/month (Prague avg)
        market_rent_per_m2 = 300 
        monthly_rent = ad.floor_area_m2 * market_rent_per_m2 if ad.floor_area_m2 else 0
        annual_rent = monthly_rent * 12
        
        # 2. Yield Calculation
        # Gross Yield = (Annual Rent / Purchase Price) * 100
        gross_yield = 0.0
        if ad.price_czk and ad.price_czk > 0:
            gross_yield = (annual_rent / ad.price_czk) * 100
            
        # 3. Decision
        is_good = gross_yield >= self.min_yield_target
        
        return FinancialMetrics(
            gross_yield_percent=round(gross_yield, 2),
            estimated_annual_rent_czk=round(annual_rent, 0),
            price_per_m2=ad.price_per_m2 or 0,
            is_good_deal=is_good
        )
