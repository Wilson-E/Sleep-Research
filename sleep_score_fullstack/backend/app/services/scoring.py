
import math
from typing import Dict, List, Tuple
from app.models.schemas import PredictRequest, BreakdownItem
from app.services.model_service import ModelService

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def log10_safe(x: float) -> float:
    return math.log10(max(1e-6, x))

# ---------------------------
# Module 1: Timing & Latency
# ---------------------------

def timing_latency_module(req: PredictRequest) -> Tuple[float, List[BreakdownItem]]:
    """
    Combines:
      - Light (Didikoglu et al., PNAS 2023): pre-bed light increases sleep onset latency; higher morning light reduces morning sleepiness.
      - Chrononutrition (Kim et al., Nutrients 2024): timing relationships reported as odds ratios; we map to a small score adjustment.

    Output: 0-100 subscore + breakdown items.
    """
    items: List[BreakdownItem] = []
    score = 100.0

    # ---- Light: pre-bed light -> SOL penalty (evidence-based)
    # Paper statement: 1 log-lux unit pre-bed is associated with +0.5h (~30 min) longer SOL.
    # We'll convert to "points": +15 min SOL -> -5 points (so +30 min -> -10 points).
    evening_log = log10_safe(req.evening_light_lux + 1e-6)
    # Set a reference point at 10 lx (recommended max in last hours); above that increases SOL.
    ref_log = log10_safe(10.0)
    delta_log = max(0.0, evening_log - ref_log)
    sol_minutes_increase = 30.0 * delta_log  # 30 min per +1 log unit
    sol_points = (sol_minutes_increase / 15.0) * 5.0
    score -= sol_points
    items.append(BreakdownItem(
        label="Light: pre-bed exposure",
        delta=-sol_points,
        details=f"Evening={req.evening_light_lux:.0f} lx → ΔSOL≈+{sol_minutes_increase:.0f} min (rule: +1 log-lux ≈ +30 min SOL)."
    ))

    # ---- Light: morning light -> morning alertness bonus (evidence-based direction)
    # We don't have a direct "points" mapping, so we use a gentle bonus:
    # reaching 250 lx (recommended daytime minimum) earns up to +6 points.
    morning_bonus = 0.0
    if req.morning_light_lux >= 250:
        morning_bonus = 6.0
    elif req.morning_light_lux >= 100:
        morning_bonus = 3.0
    else:
        morning_bonus = 0.0
    score += morning_bonus
    items.append(BreakdownItem(
        label="Light: morning exposure",
        delta=morning_bonus,
        details=f"Morning={req.morning_light_lux:.0f} lx (bonus for reaching ~250 lx daytime target)."
    ))

    # ---- Light: night light minutes (>1 lx during sleep) penalty
    night_pen = clamp(req.night_light_minutes / 30.0, 0.0, 6.0)  # up to -6 points
    score -= night_pen
    items.append(BreakdownItem(
        label="Light: night exposure",
        delta=-night_pen,
        details=f"Night light={req.night_light_minutes:.0f} min → penalty={night_pen:.1f}."
    ))

    # ---- Chrononutrition (NHANES paper): map odds-ratio relationships to modest score changes.
    # Reported: each additional hour wake→first eat increases odds of poor timing and poor duration.
    # We'll penalize >1h delay after wake modestly.
    w2e = req.hours_wake_to_first_eat
    if w2e > 1.0:
        pen = min(8.0, (w2e - 1.0) * 2.0)  # -2 points per hour beyond 1h, capped
        score -= pen
        items.append(BreakdownItem(
            label="Chrononutrition: delay to first meal",
            delta=-pen,
            details=f"Wake→1st eat={w2e:.1f} h (penalty beyond 1h)."
        ))
    else:
        items.append(BreakdownItem(
            label="Chrononutrition: delay to first meal",
            delta=0.0,
            details=f"Wake→1st eat={w2e:.1f} h."
        ))

    # last meal close to bed: each extra hour between last eat and bed associated with higher odds of poor duration
    # This is a bit counterintuitive; practical sleep hygiene often prefers *more* time before bed.
    # We'll implement a conservative rule: penalize if last meal is very close (<2h).
    leb = req.hours_last_eat_to_bed
    if leb < 2.0:
        pen = (2.0 - leb) * 3.0  # up to -6
        score -= pen
        items.append(BreakdownItem(
            label="Chrononutrition: last meal close to bed",
            delta=-pen,
            details=f"Last eat→bed={leb:.1f} h (penalty when <2h)."
        ))
    else:
        items.append(BreakdownItem(
            label="Chrononutrition: last meal close to bed",
            delta=0.0,
            details=f"Last eat→bed={leb:.1f} h."
        ))

    # eating window: 8–12h often used; in their paper, longer window associated with lower odds of poor timing.
    # We'll give a small bonus for 10–12h, mild penalty if extremely long.
    ew = req.eating_window_hours
    ew_delta = 0.0
    if 10 <= ew <= 12:
        ew_delta = 2.0
    elif ew > 14:
        ew_delta = -2.0
    score += ew_delta
    items.append(BreakdownItem(
        label="Chrononutrition: eating window",
        delta=ew_delta,
        details=f"Window={ew:.1f} h."
    ))

    score = clamp(score, 0.0, 100.0)
    return score, items

# ---------------------------
# Module 2: Disruption
# ---------------------------

def disruption_module(req: PredictRequest, models: ModelService) -> Tuple[float, List[BreakdownItem]]:
    """
    Uses the traders dataset (Song & Walker) as a row-level model:
      - Predict Duration (minutes) and SSQ (0-100) from caffeine/alcohol (+ interaction + weekend).
    Maps predicted outcomes to a 0-100 subscore.
    """
    items: List[BreakdownItem] = []
    score = 100.0

    if not models.traders:
        raise RuntimeError("Models not loaded")

    weekend = 1.0 if req.weekend else 0.0
    caf = req.caffeine_cups
    alc = req.alcohol_drinks
    X = [caf, alc, caf * alc, weekend]

    pred_dur_min = models.traders.duration_minutes.predict_one(X)
    pred_ssq = models.traders.ssq.predict_one(X)

    # Clamp to realistic ranges to avoid crazy extrapolation
    pred_dur_min = clamp(pred_dur_min, 180.0, 720.0)     # 3h..12h
    pred_ssq = clamp(pred_ssq, 0.0, 100.0)

    pred_dur_h = pred_dur_min / 60.0

    # Duration subscore: best at 7–9h
    if pred_dur_h < 7.0:
        dur_pen = (7.0 - pred_dur_h) * 12.0
    elif pred_dur_h > 9.0:
        dur_pen = (pred_dur_h - 9.0) * 8.0
    else:
        dur_pen = 0.0

    # Quality subscore: treat SSQ as direct 0-100 but downweight (subjective)
    qual_pen = (80.0 - pred_ssq) * 0.4 if pred_ssq < 80.0 else 0.0

    total_pen = dur_pen + qual_pen
    score -= total_pen

    items.append(BreakdownItem(
        label="Traders model: predicted sleep duration",
        delta=-dur_pen,
        details=f"Pred duration={pred_dur_h:.2f} h (trained on traders CSV; duration stored in minutes)."
    ))
    items.append(BreakdownItem(
        label="Traders model: predicted subjective sleep quality",
        delta=-qual_pen,
        details=f"Pred SSQ={pred_ssq:.1f}/100."
    ))

    # Extra transparency: show inputs
    items.append(BreakdownItem(
        label="Inputs: caffeine & alcohol",
        delta=0.0,
        details=f"Caffeine={caf:.1f} cups, Alcohol={alc:.1f} drinks, Weekend={int(req.weekend)}."
    ))

    score = clamp(score, 0.0, 100.0)
    return score, items

# ---------------------------
# Module 3: Recovery (HRV)
# ---------------------------

def recovery_module(req: PredictRequest) -> Tuple[float, List[BreakdownItem]]:
    """
    Starter HRV-based recovery module.
    - If RMSSD is provided: higher RMSSD -> better recovery.
    - If resting HR is provided: higher resting HR -> worse recovery.

    For now this is a calibrated mapping (data-driven model can be added once your HRV dataset is cleaned/merged).
    """
    items: List[BreakdownItem] = []
    score = 100.0

    if req.rmssd_ms is None and req.resting_hr_bpm is None:
        items.append(BreakdownItem(
            label="Recovery: HRV inputs not provided",
            delta=0.0,
            details="Provide RMSSD (ms) and/or resting HR (bpm) for recovery scoring."
        ))
        return 75.0, items  # neutral default

    # RMSSD mapping (rough): 20ms low, 50ms decent, 80ms very good
    if req.rmssd_ms is not None:
        rmssd = req.rmssd_ms
        rmssd_score = clamp((rmssd - 20.0) / (80.0 - 20.0) * 100.0, 0.0, 100.0)
        score = 0.7 * score + 0.3 * rmssd_score
        items.append(BreakdownItem(
            label="Recovery: RMSSD",
            delta=0.0,
            details=f"RMSSD={rmssd:.1f} ms → scaled={rmssd_score:.0f}/100 (starter mapping)."
        ))

    # Resting HR mapping (rough): 50 great, 70 average, 90 high
    if req.resting_hr_bpm is not None:
        rhr = req.resting_hr_bpm
        rhr_score = clamp((90.0 - rhr) / (90.0 - 50.0) * 100.0, 0.0, 100.0)
        score = 0.7 * score + 0.3 * rhr_score
        items.append(BreakdownItem(
            label="Recovery: resting HR",
            delta=0.0,
            details=f"RHR={rhr:.1f} bpm → scaled={rhr_score:.0f}/100 (starter mapping)."
        ))

    score = clamp(score, 0.0, 100.0)
    return score, items


def score_sleep(req: PredictRequest, models: ModelService) -> tuple[float, Dict[str, float], List[BreakdownItem], Dict[str, str]]:
    """
    Approach 1 (Ensemble):
      SleepScore = w1*TimingLatency + w2*Disruption + w3*Recovery
    Default weights: 0.35 / 0.35 / 0.30
    """
    w1, w2, w3 = 0.35, 0.35, 0.30

    tl_score, tl_items = timing_latency_module(req)
    dis_score, dis_items = disruption_module(req, models)
    rec_score, rec_items = recovery_module(req)

    sleep_score = w1 * tl_score + w2 * dis_score + w3 * rec_score
    sleep_score = clamp(sleep_score, 0.0, 100.0)

    components = {
        "Timing & latency": tl_score,
        "Disruption": dis_score,
        "Recovery": rec_score,
    }

    breakdown: List[BreakdownItem] = []
    # Show weighted contributions
    breakdown.append(BreakdownItem(
        label="Timing & latency module",
        delta=(w1 * tl_score) - (w1 * 100.0),
        details=f"Module score={tl_score:.1f}/100, weight={w1:.2f}."
    ))
    breakdown.extend(tl_items)

    breakdown.append(BreakdownItem(
        label="Disruption module",
        delta=(w2 * dis_score) - (w2 * 100.0),
        details=f"Module score={dis_score:.1f}/100, weight={w2:.2f}."
    ))
    breakdown.extend(dis_items)

    breakdown.append(BreakdownItem(
        label="Recovery module",
        delta=(w3 * rec_score) - (w3 * 100.0),
        details=f"Module score={rec_score:.1f}/100, weight={w3:.2f}."
    ))
    breakdown.extend(rec_items)

    model_info = {
        "approach": "Approach 1 ensemble (Timing&Latency + Disruption + Recovery)",
        "weights": f"{w1:.2f}/{w2:.2f}/{w3:.2f}",
        "notes": "Traders module trains a small OLS regression (no sklearn). Light/chrononutrition/HRV are calibrated rules (starter).",
    }

    return sleep_score, components, breakdown, model_info
