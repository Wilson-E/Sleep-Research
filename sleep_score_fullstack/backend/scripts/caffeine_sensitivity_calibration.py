from __future__ import annotations

import csv
import math
import sys
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.linreg import fit_ols

TRADERS_CSV = BACKEND_ROOT / "data" / "financial_traders_data.csv"

# Baseline pathway assumptions in the simulation engine.
BASELINE_DURATION_MIN_PER_CUP = 10.4
BASELINE_QUALITY_PTS_PER_CUP = 2.0

# Keep multipliers in same range as frontend slider.
MIN_MULTIPLIER = 0.5
MAX_MULTIPLIER = 1.5


@dataclass
class ParticipantEstimates:
    participant_id: str
    n_rows: int
    duration_min_per_cup: float
    quality_pts_per_cup: float
    raw_sensitivity: float
    unclipped_multiplier: float
    sensitivity_multiplier: float


def _safe_float(value: str) -> float | None:
    try:
        if value is None:
            return None
        value = str(value).strip()
        if value == "" or value.lower() in {"na", "nan", "none"}:
            return None
        return float(value)
    except Exception:
        return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _quantile(values: List[float], q: float) -> float:
    if not values:
        return 1.0
    values = sorted(values)
    pos = q * (len(values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    w = pos - lo
    return values[lo] * (1.0 - w) + values[hi] * w


def _raw_to_multiplier(raw_sensitivity: float) -> float:
    # Center around 1.0 and compress extremes so one outlier does not dominate.
    # raw_sensitivity ~= 1.0 means close to pathway baseline impact.
    centered = raw_sensitivity - 1.0
    return 1.0 + (0.55 * math.tanh(centered))


def _fit_effects(rows: List[Dict[str, float]]) -> tuple[float, float]:
    # Same core predictors used in the backend traders model.
    X: List[List[float]] = []
    y_duration: List[float] = []
    y_ssq: List[float] = []

    for row in rows:
        caffeine = row["caffeine"]
        alcohol = row["alcohol"]
        weekend = row["weekend"]
        duration = row["duration"]
        ssq = row["ssq"]

        X.append([caffeine, alcohol, caffeine * alcohol, weekend])
        y_duration.append(duration)
        y_ssq.append(ssq)

    dur_model = fit_ols(X, y_duration)
    ssq_model = fit_ols(X, y_ssq)

    # Coef order: caffeine, alcohol, caffeine*alcohol, weekend
    caffeine_dur_coef = dur_model.coef[0]
    caffeine_ssq_coef = ssq_model.coef[0]
    return caffeine_dur_coef, caffeine_ssq_coef


def estimate_profiles(csv_path: Path) -> List[ParticipantEstimates]:
    grouped: Dict[str, List[Dict[str, float]]] = {}

    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            pid = str(r.get("ParticipantID", "")).strip()
            if not pid:
                continue

            caffeine = _safe_float(r.get("Caffeine"))
            alcohol = _safe_float(r.get("Alcohol"))
            weekend = _safe_float(r.get("Weekend"))
            duration = _safe_float(r.get("Duration"))
            ssq = _safe_float(r.get("SSQ"))
            if None in {caffeine, alcohol, weekend, duration, ssq}:
                continue

            grouped.setdefault(pid, []).append(
                {
                    "caffeine": caffeine,
                    "alcohol": alcohol,
                    "weekend": weekend,
                    "duration": duration,
                    "ssq": ssq,
                }
            )

    estimates: List[ParticipantEstimates] = []
    for pid, rows in grouped.items():
        if len(rows) < 15:
            continue

        caffeine_values = [row["caffeine"] for row in rows]
        if max(caffeine_values) - min(caffeine_values) < 0.75:
            continue

        try:
            caffeine_dur_coef, caffeine_ssq_coef = _fit_effects(rows)
        except Exception:
            continue

        # Convert to "penalty magnitudes" so bigger means more sensitive.
        duration_min_per_cup = max(0.0, -caffeine_dur_coef)
        quality_pts_per_cup = max(0.0, -caffeine_ssq_coef)

        # Normalize against baseline pathway assumptions.
        duration_component = duration_min_per_cup / BASELINE_DURATION_MIN_PER_CUP
        quality_component = quality_pts_per_cup / BASELINE_QUALITY_PTS_PER_CUP

        # Duration carries more weight in current scoring pathway.
        raw_sensitivity = (0.7 * duration_component) + (0.3 * quality_component)
        unclipped_multiplier = _raw_to_multiplier(raw_sensitivity)
        sensitivity_multiplier = unclipped_multiplier
        sensitivity_multiplier = _clamp(sensitivity_multiplier, MIN_MULTIPLIER, MAX_MULTIPLIER)

        estimates.append(
            ParticipantEstimates(
                participant_id=pid,
                n_rows=len(rows),
                duration_min_per_cup=duration_min_per_cup,
                quality_pts_per_cup=quality_pts_per_cup,
                raw_sensitivity=raw_sensitivity,
                unclipped_multiplier=unclipped_multiplier,
                sensitivity_multiplier=sensitivity_multiplier,
            )
        )

    return sorted(estimates, key=lambda e: e.sensitivity_multiplier)


def main() -> None:
    estimates = estimate_profiles(TRADERS_CSV)
    if not estimates:
        print("No participants had enough variation to estimate sensitivity multipliers.")
        return

    multipliers = [e.unclipped_multiplier for e in estimates]

    adjusted_cutoff = _clamp(_quantile(multipliers, 0.33), MIN_MULTIPLIER, MAX_MULTIPLIER)
    sensitive_cutoff = _clamp(_quantile(multipliers, 0.67), MIN_MULTIPLIER, MAX_MULTIPLIER)

    print("Caffeine sensitivity calibration from traders dataset")
    print(f"Participants modeled: {len(estimates)}")
    print(f"Multiplier mean: {statistics.mean(multipliers):.2f}")
    print(f"Multiplier median: {statistics.median(multipliers):.2f}")
    print(f"Adjusted profile upper bound (~33rd pct): {adjusted_cutoff:.2f}")
    print(f"Sensitive profile lower bound (~67th pct): {sensitive_cutoff:.2f}")
    print()
    print("Suggested slider anchors")
    print(f"- Caffeine adjusted: {MIN_MULTIPLIER:.2f}x to {adjusted_cutoff:.2f}x")
    print(f"- Average: {adjusted_cutoff:.2f}x to {sensitive_cutoff:.2f}x")
    print(f"- Very sensitive: {sensitive_cutoff:.2f}x to {MAX_MULTIPLIER:.2f}x")
    print()
    print("Sample participant estimates (lowest 5, highest 5)")
    for e in (estimates[:5] + estimates[-5:]):
        print(
            f"PID {e.participant_id:>3} | n={e.n_rows:>3} | "
            f"dur={e.duration_min_per_cup:>5.2f} min/cup | "
            f"ssq={e.quality_pts_per_cup:>5.2f} pts/cup | "
            f"raw={e.raw_sensitivity:>5.2f} | "
            f"mult={e.sensitivity_multiplier:>4.2f}x"
        )


if __name__ == "__main__":
    main()
