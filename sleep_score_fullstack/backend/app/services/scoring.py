from typing import Dict, List, Optional

from app.models.schemas import BreakdownItem, PredictRequest
from app.services.sleep_simulation_engine import (
    AlcoholPathway,
    CaffeineDose,
    CaffeinePathway,
    EveningDietModifier,
    LightPathway,
    MealTimingPathway,
    SleepScoreCalculator,
)
from app.utils.math_utils import clamp


def _build_caffeine_doses(cups: float, weekend: bool) -> List[CaffeineDose]:
    """
    Converts total cups into plausible daytime doses. This keeps the API payload
    stable while enabling the new dose-based caffeine pathway.
    """
    if cups <= 0:
        return []

    start_hour = 9.0 if weekend else 8.0
    spacing_hours = 3.5
    whole = int(cups)
    remainder = max(0.0, cups - whole)

    doses: List[CaffeineDose] = []
    for i in range(whole):
        doses.append(CaffeineDose(time_hours_after_midnight=start_hour + i * spacing_hours, dose_mg=95.0))

    if remainder > 0:
        doses.append(
            CaffeineDose(
                time_hours_after_midnight=start_hour + whole * spacing_hours,
                dose_mg=95.0 * remainder,
            )
        )

    return doses


def _build_explicit_caffeine_doses(req: PredictRequest) -> List[CaffeineDose]:
    if not req.caffeine_doses:
        return []

    doses: List[CaffeineDose] = []
    for dose in req.caffeine_doses:
        if dose.dose_mg <= 0:
            continue
        doses.append(
            CaffeineDose(
                time_hours_after_midnight=dose.time_hours_after_midnight,
                dose_mg=dose.dose_mg,
            )
        )
    return doses


def _cups_from_doses(doses: List[CaffeineDose]) -> float:
    total_mg = sum(dose.dose_mg for dose in doses)
    return total_mg / 95.0


def _compute_evening_caffeine_mg(doses: List[CaffeineDose]) -> float:
    """Sum caffeine from doses taken at or after 18:00 (6 PM)."""
    return sum(d.dose_mg for d in doses if d.time_hours_after_midnight >= 18.0)


def _compute_evening_alcohol(req: PredictRequest, hours_last_eat_to_bed: float) -> float:
    """
    Determine how many drinks were consumed in the evening.
    Uses explicit alcohol_last_drink_time if provided; otherwise falls back to
    the meal-timing heuristic (short last-eat-to-bed window implies evening intake).
    """
    if req.alcohol_drinks <= 0:
        return 0.0
    if req.alcohol_last_drink_time is not None:
        return req.alcohol_drinks if req.alcohol_last_drink_time >= 18.0 else 0.0
    # Heuristic: if last meal was within 4h of bed, assume drinks were evening
    return req.alcohol_drinks if hours_last_eat_to_bed < 4.0 else 0.0


def _build_calculator(req: PredictRequest, profile=None) -> SleepScoreCalculator:
    wake_time = 7.5 if req.weekend else 6.5
    first_meal = wake_time + req.hours_wake_to_first_eat
    last_meal = first_meal + req.eating_window_hours
    derived_bedtime = last_meal + req.hours_last_eat_to_bed
    bedtime = req.bedtime_hours if req.bedtime_hours is not None else derived_bedtime

    # Rough proxy: convert a morning-light lux reading into equivalent hours
    # of bright-light exposure. 250 lux is the floor for "bright indoor"; above
    # that we assume one hour of effective bright exposure per 250 lux, capped
    # at 4 hours so an outdoor reading does not explode the alertness bonus.
    daytime_bright_hours = clamp(req.morning_light_lux / 250.0, 0.0, 4.0)
    explicit_doses = _build_explicit_caffeine_doses(req)
    caffeine_doses = explicit_doses or _build_caffeine_doses(req.caffeine_cups, req.weekend)
    caffeine_cups = _cups_from_doses(caffeine_doses) if explicit_doses else req.caffeine_cups

    # Derive evening-specific values for cross-pathway modifier
    evening_caffeine_mg = _compute_evening_caffeine_mg(caffeine_doses)
    evening_alcohol = _compute_evening_alcohol(req, req.hours_last_eat_to_bed)

    # Extract personalized coefficients (fall back to defaults if no profile)
    caffeine_min_per_cup = profile["caffeine_duration_min_per_cup"].mu if profile else 10.4
    caffeine_half_life = profile["caffeine_half_life_hours"].mu if profile else 6.0
    alcohol_qual_per_drink = profile["alcohol_quality_per_drink"].mu if profile else 3.04
    light_sol_per_lux = profile["light_sol_min_per_log_lux"].mu if profile else 30.0
    meal_sensitivity = profile["meal_timing_sensitivity"].mu if profile else 1.0
    evening_sensitivity = profile["evening_diet_sensitivity"].mu if profile else 1.0

    return SleepScoreCalculator(
        caffeine_pathway=CaffeinePathway(
            doses=caffeine_doses,
            bedtime_hours=bedtime,
            sensitivity_multiplier=req.caffeine_sensitivity,
            half_life_hours=caffeine_half_life,
            _minutes_lost_per_cup=caffeine_min_per_cup,
        ),
        alcohol_pathway=AlcoholPathway(
            drinks=req.alcohol_drinks,
            caffeine_cups=caffeine_cups,
            _quality_pen_per_drink=alcohol_qual_per_drink,
        ),
        meal_timing_pathway=MealTimingPathway(
            wake_time_hours=wake_time,
            first_meal_hours=first_meal,
            last_meal_hours=last_meal,
            bedtime_hours=bedtime,
            sensitivity_multiplier=meal_sensitivity,
        ),
        light_pathway=LightPathway(
            daytime_bright_light_hours=daytime_bright_hours,
            pre_bed_light_lux=req.evening_light_lux,
            night_light_minutes=req.night_light_minutes,
            _sol_min_per_log_lux=light_sol_per_lux,
        ),
        evening_diet_modifier=EveningDietModifier(
            evening_caffeine_mg=evening_caffeine_mg,
            evening_alcohol_drinks=evening_alcohol,
            hours_last_eat_to_bed=req.hours_last_eat_to_bed,
            screen_time_minutes=req.screen_time_before_bed_minutes,
            sensitivity_multiplier=evening_sensitivity,
        ),
    )


def score_sleep(
    req: PredictRequest,
    profile=None,
) -> tuple[float, Dict[str, float], List[BreakdownItem], Dict[str, str]]:
    result = _build_calculator(req, profile=profile).compute()
    comps = result["components"]

    components = {
        "Duration": comps["duration"]["score"],
        "Quality": comps["quality"]["score"],
        "Timing": comps["timing"]["score"],
        "Alertness": comps["alertness"]["score"],
    }

    personalized = profile is not None
    breakdown = [
        BreakdownItem(
            label="Duration component",
            delta=round(comps["duration"]["score"] - comps["duration"]["max"], 1),
            details=(
                f"Residual caffeine={comps['duration']['caffeine_residual_mg']:.1f} mg; "
                f"sensitivity={comps['duration']['caffeine_sensitivity_multiplier']:.2f}x; "
                f"caffeine duration penalty={comps['duration']['caffeine_duration_penalty_min']:.1f} min."
            ),
        ),
        BreakdownItem(
            label="Quality component",
            delta=round(comps["quality"]["score"] - comps["quality"]["max"], 1),
            details=(
                f"Alcohol net penalty={comps['quality']['alcohol_net_quality_penalty']:.2f}; "
                f"caffeine x alcohol offset={comps['quality']['caffeine_alcohol_interaction_offset']:.2f}; "
                f"evening diet penalty={comps['quality']['evening_diet_quality_penalty']:.2f} pts "
                f"(disturbing score={comps['quality']['evening_diet_disturbing_score']:.2f})."
            ),
        ),
        BreakdownItem(
            label="Timing component",
            delta=round(comps["timing"]["score"] - comps["timing"]["max"], 1),
            details=(
                f"Wake->first meal={comps['timing']['hours_wake_to_first_meal']:.2f} h; "
                f"last meal->bed={comps['timing']['hours_last_meal_to_bed']:.2f} h; "
                f"light latency={comps['timing']['light_latency_penalty_min']:.1f} min; "
                f"evening mediation adj={comps['timing']['evening_mediation_adjustment']:.2f} pts."
            ),
        ),
        BreakdownItem(
            label="Alertness component",
            delta=round(comps["alertness"]["score"] - comps["alertness"]["max"], 1),
            details=(
                f"Daytime alertness score={comps['alertness']['daytime_alertness_score']:.1f}/100; "
                f"night light={comps['alertness']['night_light_minutes']:.1f} min; "
                f"screen time penalty={comps['alertness']['screen_time_penalty_pts']:.2f} pts."
            ),
        ),
    ]

    model_info = {
        "approach": "Pathway-based simulation engine with cross-pathway mediation",
        "weights": "Duration 30 / Quality 30 / Timing 20 / Alertness 20",
        "notes": (
            "Uses caffeine, alcohol, meal timing, and light pathways with study-based coefficients. "
            "Cross-pathway mediation via Soares et al. (2025). "
            + ("Personalized coefficients active." if personalized else "Default population coefficients.")
        ),
    }

    return result["total_score"], components, breakdown, model_info
