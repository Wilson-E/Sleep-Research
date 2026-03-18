from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class PredictRequest(BaseModel):
    # Caffeine / alcohol
    caffeine_cups: float = Field(0, ge=0, le=20)
    alcohol_drinks: float = Field(0, ge=0, le=30)
    weekend: bool = False

    # Light (melanopic EDI proxies; user-entered)
    morning_light_lux: float = Field(100, ge=0, le=20000, description="Approx. melanopic EDI lux after waking")
    evening_light_lux: float = Field(30, ge=0, le=20000, description="Approx. melanopic EDI lux in the last ~30 min before bed")
    night_light_minutes: float = Field(0, ge=0, le=480, description="Minutes of >1 lux light during sleep")

    # Chrononutrition (from Kim et al. NHANES paper)
    hours_wake_to_first_eat: float = Field(1, ge=0, le=12)
    hours_last_eat_to_bed: float = Field(3, ge=0, le=12)
    eating_window_hours: float = Field(12, ge=0, le=24)
    # Recovery (HRV)
    rmssd_ms: Optional[float] = Field(None, ge=0, le=300, description="RMSSD in milliseconds")
    resting_hr_bpm: Optional[float] = Field(None, ge=0, le=200, description="Resting heart rate in bpm")


    # Optional personalization (if user has baseline)
    baseline_sleep_score: float = Field(75, ge=0, le=100)

class BreakdownItem(BaseModel):
    label: str
    delta: float
    details: str

class PredictResponse(BaseModel):
    sleep_score: float
    components: Dict[str, float]
    breakdown: List[BreakdownItem]
    model_info: Dict[str, str]
