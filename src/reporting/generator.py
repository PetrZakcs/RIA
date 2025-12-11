from typing import List, Tuple
from src.cleaner.models import CleanPropertyAd
from src.reporting.analysis import FinancialMetrics

class ReportGenerator:
    @staticmethod
    def generate_markdown(results: List[Tuple[CleanPropertyAd, FinancialMetrics]]) -> str:
        if not results:
            return "# RIA Investment Report\n\nNo properties found matching criteria."
            
        # Sort by Yield (Decending)
        sorted_results = sorted(results, key=lambda x: x[1].gross_yield_percent, reverse=True)
        
        md = "# 🏢 RIA Investment Memorandum (MVP)\n\n"
        md += f"**Analyzed Candidates:** {len(results)}\n"
        md += f"**Top Recommendations:**\n\n"
        
        for i, (ad, metrics) in enumerate(sorted_results[:5]): # Top 5
            icon = "✅" if metrics.is_good_deal else "⚠️"
            md += f"## {i+1}. {ad.layout_normalized or 'Unknown'} ({ad.floor_area_m2} m²)\n"
            md += f"- **Price:** {ad.price_czk:,.0f} CZK\n"
            md += f"- **Yield:** {icon} **{metrics.gross_yield_percent}% p.a.**\n"
            md += f"- **Est. Rent:** {metrics.estimated_annual_rent_czk / 12:,.0f} CZK/month\n"
            md += f"- **Location:** {ad.district} (Dist: {ad.dist_center_km} km)\n"
            md += f"- [Link to Original]({ad.source_url})\n\n"
            
        return md
