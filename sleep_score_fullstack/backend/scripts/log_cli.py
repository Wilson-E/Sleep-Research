"""
Terminal twin of the History page: log a completed night and fire the
Bayesian updater without running the FastAPI server or the React frontend.

Interactively prompts for the evening inputs (same fields as the Simulator)
and the four 1-to-5 morning-outcome sliders used on the History page, then
writes directly to backend/data/logs/<user_id>.json via SleepLogStore and
runs BayesianPersonalizer.update_from_log in-process.

Usage (from inside sleep_score_fullstack/backend):

  # Interactive prompt flow, prompts for everything:
  python scripts/log_cli.py

  # Non-interactive defaults:
  python scripts/log_cli.py --defaults --user-id cli_test

  # Preset a specific user and date, then prompt for everything else:
  python scripts/log_cli.py --user-id billy --date 2026-04-18

  # Scripted mode, read a JSON file whose keys match field names (both
  # evening inputs and the five outcome fields, optionally user_id and date):
  python scripts/log_cli.py --input night.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.models.schemas import PredictRequest
from app.services.bayesian_updater import BayesianPersonalizer
from app.services.scoring import score_sleep
from app.services.sleep_log import SleepLogEntry, SleepLogStore

LOG_DIR = BACKEND / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


EVENING_PROMPTS = [
    ("caffeine_cups",                    "Caffeine cups consumed yesterday",               "0"),
    ("caffeine_sensitivity",             "Caffeine sensitivity multiplier (0.25 to 2.0)",  "1.0"),
    ("alcohol_drinks",                   "Alcoholic drinks yesterday evening",             "0"),
    ("alcohol_last_drink_time",          "Hour of last drink (0 to 24, blank if none)",    ""),
    ("weekend",                          "Weekend night? (y/n)",                           "n"),
    ("bedtime_hours",                    "Bedtime hour (0 to 24, blank for auto)",         ""),
    ("morning_light_lux",                "Morning light exposure (lux)",                   "100"),
    ("evening_light_lux",                "Evening light (last 30 min before bed, lux)",    "30"),
    ("night_light_minutes",              "Minutes of light above 1 lux during sleep",      "0"),
    ("hours_wake_to_first_eat",          "Hours between waking and first meal",            "1"),
    ("hours_last_eat_to_bed",            "Hours between last meal and bedtime",            "3"),
    ("eating_window_hours",              "Length of eating window (hours)",                "12"),
    ("screen_time_before_bed_minutes",   "Minutes of screen time in the hour before bed",  "0"),
    ("rmssd_ms",                         "RMSSD in ms (blank if unknown)",                 ""),
    ("resting_hr_bpm",                   "Resting heart rate in bpm (blank if unknown)",   ""),
    ("baseline_sleep_score",             "Usual baseline sleep score (0 to 100)",          "75"),
]

OUTCOME_PROMPTS = [
    ("quality",    "Overall sleep quality (1 terrible, 5 excellent)",           "3"),
    ("alertness",  "Morning alertness (1 exhausted, 5 refreshed)",              "3"),
    ("latency",    "Time to fall asleep (1 over an hour, 5 under 5 min)",       "3"),
    ("duration",   "Hours slept (1 under 5h, 5 over 8h)",                       "3"),
    ("awakenings", "Number of awakenings (integer count)",                      "0"),
]


BOOL_FIELDS = {"weekend"}
EVENING_OPTIONAL = {"alcohol_last_drink_time", "bedtime_hours", "rmssd_ms", "resting_hr_bpm"}
LATENCY_MINUTES = [75, 45, 22, 10, 3]
DURATION_HOURS = [4.5, 5.5, 6.5, 7.5, 8.5]


def _parse_evening(field: str, raw: str) -> Any:
    raw = raw.strip()
    if raw == "":
        if field in EVENING_OPTIONAL:
            return None
        raise ValueError(f"{field} is required")
    if field in BOOL_FIELDS:
        return raw.lower() in {"y", "yes", "true", "1"}
    return float(raw)


def _parse_outcome(field: str, raw: str) -> int:
    raw = raw.strip() or "3"
    value = int(float(raw))
    if field == "awakenings":
        if value < 0 or value > 30:
            raise ValueError("awakenings must be 0 to 30")
        return value
    if value < 1 or value > 5:
        raise ValueError(f"{field} must be 1 to 5")
    return value


def _ask(label: str, default: str) -> str:
    display = f"[{default}]" if default != "" else "[skip]"
    try:
        raw = input(f"  {label} {display}: ")
    except EOFError:
        raw = ""
    return raw if raw.strip() != "" else default


def prompt_evening() -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    print("\nEvening inputs (what happened yesterday)")
    print("Press Enter to accept the default in square brackets.\n")
    for field, label, default in EVENING_PROMPTS:
        raw = _ask(label, default)
        try:
            parsed = _parse_evening(field, raw)
        except ValueError as exc:
            print(f"    could not parse {field!r}: {exc}. Using default.", file=sys.stderr)
            parsed = _parse_evening(field, default) if default else None
        if parsed is not None:
            values[field] = parsed
    return values


def prompt_outcomes() -> Dict[str, int]:
    values: Dict[str, int] = {}
    print("\nMorning outcomes (how you slept)")
    for field, label, default in OUTCOME_PROMPTS:
        raw = _ask(label, default)
        try:
            values[field] = _parse_outcome(field, raw)
        except ValueError as exc:
            print(f"    could not parse {field!r}: {exc}. Using default.", file=sys.stderr)
            values[field] = _parse_outcome(field, default)
    return values


def default_evening() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for field, _label, default in EVENING_PROMPTS:
        if default == "":
            continue
        out[field] = _parse_evening(field, default)
    return out


def default_outcomes() -> Dict[str, int]:
    return {field: _parse_outcome(field, default) for field, _label, default in OUTCOME_PROMPTS}


def load_input_file(path: Path) -> Dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object at the top level.")
    return data


def build_entry(
    predict_req: PredictRequest,
    score: float,
    components: Dict[str, float],
    date_str: str,
) -> SleepLogEntry:
    """Mirror the SleepLogEntry construction in app/main.py log_night()."""
    timestamp = datetime.now(timezone.utc).isoformat()

    wake_time = 7.5 if predict_req.weekend else 6.5
    first_meal = wake_time + predict_req.hours_wake_to_first_eat
    last_meal = first_meal + predict_req.eating_window_hours
    derived_bedtime = last_meal + predict_req.hours_last_eat_to_bed
    bedtime = (
        predict_req.bedtime_hours if predict_req.bedtime_hours is not None else derived_bedtime
    )

    if predict_req.caffeine_doses:
        caffeine_doses = [
            {"time": d.time_hours_after_midnight, "mg": d.dose_mg}
            for d in predict_req.caffeine_doses
        ]
    else:
        caffeine_doses = []

    return SleepLogEntry(
        date=date_str,
        timestamp=timestamp,
        caffeine_doses=caffeine_doses,
        alcohol_drinks=predict_req.alcohol_drinks,
        alcohol_last_drink_time=predict_req.alcohol_last_drink_time,
        morning_light_lux=predict_req.morning_light_lux,
        evening_light_lux=predict_req.evening_light_lux,
        night_light_minutes=predict_req.night_light_minutes,
        hours_wake_to_first_eat=predict_req.hours_wake_to_first_eat,
        hours_last_eat_to_bed=predict_req.hours_last_eat_to_bed,
        eating_window_hours=predict_req.eating_window_hours,
        bedtime_hours=bedtime,
        screen_time_before_bed_minutes=predict_req.screen_time_before_bed_minutes,
        weekend=predict_req.weekend,
        predicted_score=score,
        predicted_components=components,
    )


def observed_from_outcomes(outcomes: Dict[str, int]) -> Dict[str, Any]:
    """Map the five outcome fields to the backend's observed schema."""
    quality = int(outcomes["quality"])
    alertness = int(outcomes["alertness"])
    latency = int(outcomes["latency"])
    duration = int(outcomes["duration"])
    return {
        "observed_sleep_quality_subjective": quality,
        "observed_morning_alertness": alertness,
        "observed_sleep_onset_latency_minutes": float(LATENCY_MINUTES[latency - 1]),
        "observed_sleep_duration_hours": float(DURATION_HOURS[duration - 1]),
        "observed_awakenings": int(outcomes.get("awakenings", 0)),
    }


def print_summary(
    user_id: str,
    date_str: str,
    score: float,
    observed_score: Optional[float],
    prior_profile: Dict[str, Any],
    updated_profile: Dict[str, Any],
) -> None:
    print()
    print("=" * 64)
    print(f"  Logged night for user_id={user_id!r} on {date_str}")
    print("=" * 64)
    print(f"  Predicted score:  {score:5.1f} / 100")
    if observed_score is not None:
        print(f"  Observed score:   {observed_score:5.1f} / 100")
        print(f"  Residual:         {score - observed_score:+5.1f} (predicted minus observed)")
    else:
        print("  Observed score:   unavailable")

    print("\n  Coefficient drift (prior -> posterior):")
    for name, prior in prior_profile.items():
        after = updated_profile.get(name)
        if after is None:
            continue
        before_mu = prior.mu
        after_mu = after.mu
        delta = after_mu - before_mu
        marker = "  " if abs(delta) < 1e-4 else "->"
        print(f"    {marker} {name:<36} {before_mu:8.4f}  ->  {after_mu:8.4f}  (delta {delta:+.4f})")

    print(f"\n  Saved at: {LOG_DIR / (user_id + '.json')}")
    print()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Log a completed night from the terminal (CLI twin of the History page).",
    )
    p.add_argument("--input", type=Path, default=None,
                   help="JSON file with evening and outcome fields (and optional user_id, date).")
    p.add_argument("--defaults", action="store_true",
                   help="Skip prompts; use defaults for every field.")
    p.add_argument("--user-id", default=None, help="Preset the user ID (skips the prompt).")
    p.add_argument("--date", default=None, help="Preset the night date (YYYY-MM-DD).")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    evening: Dict[str, Any]
    outcomes: Dict[str, int]
    user_id: Optional[str] = args.user_id
    date_str: Optional[str] = args.date

    if args.input is not None:
        data = load_input_file(args.input)
        user_id = user_id or data.pop("user_id", None)
        date_str = date_str or data.pop("date", None)
        outcomes_src = {k: data.pop(k) for k in list(data.keys()) if k in {p[0] for p in OUTCOME_PROMPTS}}
        evening = data
        outcomes = {k: _parse_outcome(k, str(v)) for k, v in outcomes_src.items()}
        for field, _label, default in OUTCOME_PROMPTS:
            outcomes.setdefault(field, _parse_outcome(field, default))
    elif args.defaults:
        evening = default_evening()
        outcomes = default_outcomes()
    else:
        if not user_id:
            user_id = _ask("User ID for this entry", "default_user")
        if not date_str:
            date_str = _ask("Night date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
        evening = prompt_evening()
        outcomes = prompt_outcomes()

    if not user_id:
        user_id = "default_user"
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    evening.setdefault("user_id", user_id)
    predict_req = PredictRequest(**evening)

    personalizer = BayesianPersonalizer(LOG_DIR)
    store = SleepLogStore(LOG_DIR)

    prior_profile = personalizer.get_profile(user_id)
    score, components, _breakdown, _info = score_sleep(predict_req, profile=prior_profile)

    entry = build_entry(predict_req, score, components, date_str)
    store.add_entry(user_id, entry)

    observed = observed_from_outcomes(outcomes)
    updated_entry = store.update_entry_observed(user_id, date_str, observed)
    if updated_entry is None:
        print(f"Error: could not find just-written entry for {date_str}.", file=sys.stderr)
        return 1

    updated_profile = personalizer.update_from_log(user_id, updated_entry)
    print_summary(
        user_id,
        date_str,
        score,
        updated_entry.observed_score,
        prior_profile,
        updated_profile,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
