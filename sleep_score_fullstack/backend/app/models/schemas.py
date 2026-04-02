from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class CaffeineDoseInput(BaseModel):
    time_hours_after_midnight: float = Field(8.0, ge=0, le=24)
    dose_mg: float = Field(95.0, ge=0, le=1000)

class PredictRequest(BaseModel):
    # Caffeine / alcohol
    caffeine_cups: float = Field(0, ge=0, le=20)
    caffeine_sensitivity: float = Field(
        1.0,
        ge=0.25,
        le=2.0,
        description="Personalized caffeine sensitivity multiplier. <1 means caffeine-adjusted (less effect), >1 means caffeine-sensitive (stronger effect).",
    )
    caffeine_doses: Optional[List[CaffeineDoseInput]] = Field(
        None,
        description="Optional explicit caffeine doses with intake times. If omitted, backend derives a default schedule from caffeine_cups.",
    )
    alcohol_drinks: float = Field(0, ge=0, le=30)
    alcohol_last_drink_time: Optional[float] = Field(
        None,
        ge=0,
        le=24,
        description="Time of last alcoholic drink (hours after midnight). If omitted, assumes evening if bedtime is within 4h of last meal.",
    )
    weekend: bool = False
    bedtime_hours: Optional[float] = Field(
        None,
        ge=0,
        le=24,
        description="Optional explicit bedtime hour (0-24). If omitted, bedtime is derived from meal timing fields.",
    )

    # Light (melanopic EDI proxies; user-entered)
    morning_light_lux: float = Field(100, ge=0, le=20000, description="Approx. melanopic EDI lux after waking")
    evening_light_lux: float = Field(30, ge=0, le=20000, description="Approx. melanopic EDI lux in the last ~30 min before bed")
    night_light_minutes: float = Field(0, ge=0, le=480, description="Minutes of >1 lux light during sleep")

    # Chrononutrition (from Kim et al. NHANES paper)
    hours_wake_to_first_eat: float = Field(1, ge=0, le=12)
    hours_last_eat_to_bed: float = Field(3, ge=0, le=12)
    eating_window_hours: float = Field(12, ge=0, le=24)

    # Evening diet / screen time (Soares et al. 2025)
    screen_time_before_bed_minutes: float = Field(
        0,
        ge=0,
        le=480,
        description="Minutes of screen time in the hour before bed",
    )

    # Recovery (HRV)
    rmssd_ms: Optional[float] = Field(None, ge=0, le=300, description="RMSSD in milliseconds")
    resting_hr_bpm: Optional[float] = Field(None, ge=0, le=200, description="Resting heart rate in bpm")

    # Optional personalization (if user has baseline)
    baseline_sleep_score: float = Field(75, ge=0, le=100)

    # User ID for Bayesian personalization (optional; uses defaults if omitted)
    user_id: Optional[str] = Field(None, min_length=1, max_length=64, description="User ID for personalized coefficient profile")


class BreakdownItem(BaseModel):
    label: str
    delta: float
    details: str

class PredictResponse(BaseModel):
    sleep_score: float
    components: Dict[str, float]
    breakdown: List[BreakdownItem]
    model_info: Dict[str, str]


# ---------------------------------------------------------------------------
# Sleep Log schemas
# ---------------------------------------------------------------------------

class SleepLogRequest(BaseModel):
    """Submitted when user logs their evening inputs."""
    user_id: str = Field("default", min_length=1, max_length=64)
    predict_request: PredictRequest
    date: Optional[str] = Field(None, description="ISO date (YYYY-MM-DD); defaults to today")


class ObservedOutcomeRequest(BaseModel):
    """Submitted the morning after a logged night."""
    user_id: str = Field("default", min_length=1, max_length=64)
    observed_sleep_duration_hours: Optional[float] = Field(None, ge=0, le=24)
    observed_sleep_quality_subjective: Optional[int] = Field(None, ge=1, le=5)
    observed_sleep_onset_latency_minutes: Optional[float] = Field(None, ge=0, le=480)
    observed_awakenings: Optional[int] = Field(None, ge=0, le=30)
    observed_morning_alertness: Optional[int] = Field(None, ge=1, le=5)


class SleepLogResponse(BaseModel):
    entries: List[Dict]
    total_entries: int


class SleepLogStatsResponse(BaseModel):
    user_id: str
    total_entries: int
    entries_with_outcomes: int
    avg_predicted_score: Optional[float]
    avg_observed_score: Optional[float]
    avg_residual: Optional[float]


class UserProfileResponse(BaseModel):
    user_id: str
    total_logs: int
    logs_with_outcomes: int
    personalized_coefficients: Dict[str, float]
    coefficient_confidence: Dict[str, float]
    base_coefficients: Dict[str, float]
