from typing import List, Dict
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str

class StressItem(BaseModel):
    fips: str
    date: str
    CSI: float
    category: str

class StressResponse(BaseModel):
    results: List[StressItem]
    note: str

class DatesResponse(BaseModel):
    dates: List[str]

class CountyItem(BaseModel):
    fips: str
    county_name: str

class CountiesResponse(BaseModel):
    counties: List[CountyItem]

class StressProbResponse(BaseModel):
    fips: str
    date: str
    season_progress: float
    features_used: List[str]
    prediction: Dict[str, float]
    contributions: Dict[str, Dict[str, float]]
    explanation: str
