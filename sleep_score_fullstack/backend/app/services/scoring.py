import math
from typing import Dict, List
from app.models.schemas import PredictRequest, BreakdownItem
from app.services.model_service import ModelService


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _log10_safe(x: float) -> float:
    return math.log10(max(1e-6, x))


def score_sleep(req: PredictRequest, models: ModelService) -> tuple[float, Dict[str, float], List[BreakdownItem], Dict[str, str]]:
    """Compute a 0-100 Sleep Score + breakdown.

    Starter design:
    - Baseline comes from baseline_sleep_score.
    - Data-driven deltas come from trained regressions on the two available CSV datasets.
    - Evidence-based deltas for light + chrononutrition are rule-based, derived from paper directionality + magnitude.

    You can later replace the rule-based parts with learned models if you collect unified data.
    """

    breakdown: List[BreakdownItem] = []

    # ── 1) Traders model: predicted duration + subjective sleep quality (SSQ)
    X_tr = {
        "caffeine": req.caffeine_cups,
        "alcohol": req.alcohol_drinks,
        "caf_x_alc": req.caffeine_cups * req.alcohol_drinks,
        "weekend": int(req.weekend),
    }
    trX = [[X_tr["caffeine"], X_tr["alcohol"], X_tr["caf_x_alc"], X_tr["weekend"]]]
    pred_duration = float(models.traders.duration_model.predict(trX)[0])
    pred_ssq = float(models.traders.ssq_model.predict(trX)[0])

    # Convert to penalties/bonuses
    duration_pen = 0.0
    if pred_duration < 7:
        duration_pen += (7 - pred_duration) * 10.0
    if pred_duration > 9:
        duration_pen += (pred_duration - 9) * 5.0

    ssq_bonus = (pred_ssq - 72.0) * 0.15  # gentle scaling around dataset mean ~72

    breakdown.append(BreakdownItem(
        label="Caffeine/Alcohol (Traders model)",
        delta=ssq_bonus - duration_pen,
        details=f"Pred SSQ={pred_ssq:.1f}/100, Pred duration={pred_duration:.2f}h",
    ))

    # ── 2) Didikoglu model: predicted sleep onset latency (SOL)
    workday = 0 if req.weekend else 1
    didX = [[req.caffeine_cups, req.alcohol_drinks, req.caffeine_cups * req.alcohol_drinks, workday]]
    pred_latency_h = float(models.didikoglu.latency_model.predict(didX)[0])
    # penalty after 15 min
    latency_pen = max(0.0, pred_latency_h - 0.25) * 20.0

    breakdown.append(BreakdownItem(
        label="Sleep onset latency (Didikoglu diary model)",
        delta=-latency_pen,
        details=f"Pred SOL={pred_latency_h*60:.0f} min",
    ))

    # ── 3) Light adjustments (PNAS 2023 directionality; rule-based)
    # Evidence:
    # - Meeting ~250 lx in daytime is associated with lower morning sleepiness.
    # - Pre-bed light in the last ~30 min associates with longer SOL (~0.5h per +1 log lx in paper).
    # - Light during sleep is common; more night light generally undesirable.

    # Morning light: bonus if >=250, penalty if very low
    morning_bonus = 0.0
    if req.morning_light_lux >= 250:
        morning_bonus += 3.0
    else:
        morning_bonus -= (250 - req.morning_light_lux) / 250.0 * 3.0

    # Evening light: emulate ~+0.5h SOL per +1 log10(lux) (very rough), converted to score penalty
    # Use 10 lx as a low reference; penalties grow when well above 10 lx.
    evening_log = _log10_safe(req.evening_light_lux + 1.0)
    ref_log = _log10_safe(10 + 1.0)
    extra_log = max(0.0, evening_log - ref_log)
    # 0.5h per log unit -> minutes -> score
    evening_latency_minutes = extra_log * 30.0
    evening_pen = evening_latency_minutes / 5.0  # 5 minutes ~ 1 point

    # Night light minutes: mild penalty
    night_pen = req.night_light_minutes / 30.0  # 30 min = 1 point

    light_delta = morning_bonus - evening_pen - night_pen
    breakdown.append(BreakdownItem(
        label="Light (rule-based from PNAS)",
        delta=light_delta,
        details=f"Morning={req.morning_light_lux:.0f} lx, Evening={req.evening_light_lux:.0f} lx, Night={req.night_light_minutes:.0f} min",
    ))

    # ── 4) Chrononutrition adjustments (Nutrients 2024; rule-based)
    # Directional mapping from reported odds ratios:
    # - Longer delay to first eating (per hour) worsens timing/duration.
    # - Shorter gap between last eating and bedtime worsens duration.
    # - Longer eating window slightly improves timing in the paper (OR ~0.90 per hour).

    chrono_pen = 0.0

    if req.hours_wake_to_first_eat > 1.0:
        chrono_pen += (req.hours_wake_to_first_eat - 1.0) * 1.5

    if req.hours_last_eat_to_bed < 3.0:
        chrono_pen += (3.0 - req.hours_last_eat_to_bed) * 2.0

    # small benefit if eating window is not extremely long
    chrono_bonus = 0.0
    if 8.0 <= req.eating_window_hours <= 12.0:
        chrono_bonus += 1.0
    elif req.eating_window_hours > 14.0:
        chrono_pen += (req.eating_window_hours - 14.0) * 0.5

    chrono_delta = chrono_bonus - chrono_pen
    breakdown.append(BreakdownItem(
        label="Chrononutrition (rule-based from NHANES)",
        delta=chrono_delta,
        details=f"Wake→1st eat={req.hours_wake_to_first_eat:.1f}h, Last eat→bed={req.hours_last_eat_to_bed:.1f}h, Window={req.eating_window_hours:.1f}h",
    ))

    # ── Combine
    score = req.baseline_sleep_score
    for b in breakdown:
        score += b.delta

    score = clamp(score, 0.0, 100.0)

    components = {
        "baseline": req.baseline_sleep_score,
        "traders_model": ssq_bonus - duration_pen,
        "latency_model": -latency_pen,
        "light": light_delta,
        "chrononutrition": chrono_delta,
    }

    model_info = {
        "traders": "LinearRegression(Duration, SSQ) trained on financial_traders_data.csv",
        "didikoglu": "LinearRegression(SOL) trained on Didikoglu_et_al_2023_PNAS_sleep.csv",
        "light": "Rule-based mapping from Didikoglu et al. (PNAS 2023) effect directions",
        "chrononutrition": "Rule-based mapping from Kim et al. (Nutrients 2024) reported OR directions",
    }

    return score, components, breakdown, model_info
