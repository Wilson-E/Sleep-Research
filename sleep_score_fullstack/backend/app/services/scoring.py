from typing import Dict, List

from app.models.schemas import BreakdownItem, PredictRequest
from app.services.sleep_simulation_engine import (
    AlcoholPathway,
    CaffeineDose,
    CaffeinePathway,
    LightPathway,
    MealTimingPathway,
    SleepScoreCalculator,
)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


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


def _build_calculator(req: PredictRequest) -> SleepScoreCalculator:
    wake_time = 7.5 if req.weekend else 6.5
    first_meal = wake_time + req.hours_wake_to_first_eat
    last_meal = first_meal + req.eating_window_hours
    derived_bedtime = last_meal + req.hours_last_eat_to_bed
    bedtime = req.bedtime_hours if req.bedtime_hours is not None else derived_bedtime

    daytime_bright_hours = _clamp(req.morning_light_lux / 250.0, 0.0, 4.0)
    explicit_doses = _build_explicit_caffeine_doses(req)
    caffeine_doses = explicit_doses or _build_caffeine_doses(req.caffeine_cups, req.weekend)
    caffeine_cups = _cups_from_doses(caffeine_doses) if explicit_doses else req.caffeine_cups

    return SleepScoreCalculator(
        caffeine_pathway=CaffeinePathway(
            doses=caffeine_doses,
            bedtime_hours=bedtime,
            sensitivity_multiplier=req.caffeine_sensitivity,
        ),
        alcohol_pathway=AlcoholPathway(
            drinks=req.alcohol_drinks,
            caffeine_cups=caffeine_cups,
        ),
        meal_timing_pathway=MealTimingPathway(
            wake_time_hours=wake_time,
            first_meal_hours=first_meal,
            last_meal_hours=last_meal,
            bedtime_hours=bedtime,
        ),
        light_pathway=LightPathway(
            daytime_bright_light_hours=daytime_bright_hours,
            pre_bed_light_lux=req.evening_light_lux,
            night_light_minutes=req.night_light_minutes,
        ),
    )


def score_sleep(req: PredictRequest) -> tuple[float, Dict[str, float], List[BreakdownItem], Dict[str, str]]:
    result = _build_calculator(req).compute()
    comps = result["components"]

    components = {
        "Duration": comps["duration"]["score"],
        "Quality": comps["quality"]["score"],
        "Timing": comps["timing"]["score"],
        "Alertness": comps["alertness"]["score"],
    }

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
                f"caffeine x alcohol offset={comps['quality']['caffeine_alcohol_interaction_offset']:.2f}."
            ),
        ),
        BreakdownItem(
            label="Timing component",
            delta=round(comps["timing"]["score"] - comps["timing"]["max"], 1),
            details=(
                f"Wake->first meal={comps['timing']['hours_wake_to_first_meal']:.2f} h; "
                f"last meal->bed={comps['timing']['hours_last_meal_to_bed']:.2f} h; "
                f"light latency={comps['timing']['light_latency_penalty_min']:.1f} min."
            ),
        ),
        BreakdownItem(
            label="Alertness component",
            delta=round(comps["alertness"]["score"] - comps["alertness"]["max"], 1),
            details=(
                f"Daytime alertness score={comps['alertness']['daytime_alertness_score']:.1f}/100; "
                f"night light={comps['alertness']['night_light_minutes']:.1f} min."
            ),
        ),
    ]

    model_info = {
        "approach": "Pathway-based simulation engine",
        "weights": "Duration 30 / Quality 30 / Timing 20 / Alertness 20",
        "notes": "Uses caffeine, alcohol, meal timing, and light pathways with study-based coefficients.",
    }

    return result["total_score"], components, breakdown, model_info
