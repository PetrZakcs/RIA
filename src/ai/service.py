import os
import json
from loguru import logger
from src.ai.models import SWOTAnalysis

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key and OpenAI:
            self.client = OpenAI(api_key=self.api_key)
        else:
            logger.warning("OPENAI_API_KEY not set. AI Service running in MOCK mode.")

    def analyze_property(self, title: str, description: str, price: float, yield_pct: float) -> SWOTAnalysis:
        """
        Generates a SWOT analysis for a property.
        Uses OpenAI if available, otherwise returns deterministic Mock data.
        """
        if self.client:
            return self._analyze_with_gpt(title, description, price, yield_pct)
        else:
            return self._analyze_mock(title, price, yield_pct)

    def _analyze_with_gpt(self, title: str, description: str, price: float, yield_pct: float) -> SWOTAnalysis:
        prompt = f"""
        Analyze this real estate listing for an investor.
        Title: {title}
        Price: {price} CZK
        Yield: {yield_pct:.2f}%
        Description: {description}
        
        Return a JSON object with:
        - strengths (list of strings)
        - weaknesses (list of strings)
        - verdict (short summary)
        - score (0-100 integer)
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "You are a senior real estate investment analyst. Output valid JSON only."},
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return SWOTAnalysis(**data)
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return self._analyze_mock(title, price, yield_pct)

    def _analyze_mock(self, title: str, price: float, yield_pct: float) -> SWOTAnalysis:
        # Simple heuristic mock
        strengths = []
        weaknesses = []
        
        if yield_pct > 5.0:
            strengths.append(f"Vysoký výnos ({yield_pct:.1f}%)")
        else:
            weaknesses.append(f"Nízký výnos ({yield_pct:.1f}%)")
            
        if "rekonstrukce" in title.lower():
            weaknesses.append("Nutná rekonstrukce (zohledněno v ceně?)")
            strengths.append("Možnost zhodnocení rekonstrukcí")
        else:
            strengths.append("Pravděpodobně dobrý stav")

        if price < 3_000_000:
            strengths.append("Dostupná cena pro začínající investory")
        
        score = min(int(yield_pct * 15), 100)
        
        return SWOTAnalysis(
            strengths=strengths,
            weaknesses=weaknesses,
            verdict="Toto je automaticky generovaná analýza (Mock). Pro plnou AI analýzu zadejte API klíč.",
             score=score
        )

ai_service = AIService()
