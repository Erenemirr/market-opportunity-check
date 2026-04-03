from pydantic import BaseModel, Field
from typing import List

class MarketAnalysisResult(BaseModel):
    verdict: str = Field(description="Must be exactly: 'GO', 'PROCEED WITH CAUTION', or 'DONT RECOMMEND'")
    demand_score: int = Field(description="Score from 0 to 10 based on search trend momentum")
    competition_score: int = Field(description="Score from 0 to 10 based on competitive search density")
    social_score: int = Field(description="Score from 0 to 10 based on social sentiment/complaints")
    final_score: int = Field(description="Total Opportunity Score out of 100")
    
    best_markets: List[str] = Field(description="1-3 suggested specific sub-markets, niches, or locations")
    reasons: List[str] = Field(description="3 solid reasons why this idea works or fails")
    risks: List[str] = Field(description="1-3 major risks (e.g., specific consumer complaints found)")
    next_move: str = Field(description="One actionable next step for the founder")
