from pydantic import BaseModel, Field
from typing import List, Optional

class SWOTAnalysis(BaseModel):
    strengths: List[str] = Field(description="List of strong selling points")
    weaknesses: List[str] = Field(description="List of potential risks or negatives")
    verdict: str = Field(description="Short summary conclusion (1-2 sentences)")
    score: int = Field(description="Investment score 0-100", ge=0, le=100)

class ChatMessage(BaseModel):
    role: str # "user", "assistant", "system"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context_filters: Optional[dict] = None
