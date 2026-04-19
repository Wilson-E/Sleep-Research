"""
Interactive command-line sleep-score predictor.

Prompts the user for each behavioral input that the web simulator collects,
runs the same pathway engine that powers `POST /api/predict`, and prints the
composite 0 to 100 score together with the per-pathway breakdown. Exists so
reviewers and researchers can reproduce predictions without standing up the
FastAPI server or the React frontend.

Usage:
  cd sleep_score_fullstack/backend

  # Interactive mode (prompts for each field, Enter accepts the default):
  python scripts/predict_cli.py

  # Scripted mode (read a JSON file mapping field names to values):
  python scripts/predict_cli.py --input profile.json

  # Defaults-only mode (no prompts, print the score for the default profile):
  python scripts/predict_cli.py --defaults
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.models.schemas import PredictRequest
from app.services.scoring import score_sleep


PROMPTS = [
    ("caffeine_cups",                    "Caffeine cups consumed today",                    "0"),
    ("caffeine_sensitivity",             "Caffeine sensitivity multiplier (0.25 to 2.0)",    "1.0"),
    ("alcohol_drinks",                   "Alcoholic drinks tonight",                         "0"),
    ("alcohol_last_drink_time",          "Hour of last drink (0 to 24, blank if none)",      ""),
    ("weekend",                          "Weekend night? (y/n)",                             "n"),
    ("bedtime_hours",                    "Planned bedtime hour (0 to 24, blank for auto)",   ""),
    ("morning_light_lux",                "Morning light exposure (lux)",                     "100"),
    ("evening_light_lux",                "Evening light (last 30 min before bed, lux)",      "30"),
    ("night_light_minutes",              "Minutes of light above 1 lux during sleep",        "0"),
    ("hours_wake_to_first_eat",          "Hours between waking and first meal",              "1"),
    ("hours_last_eat_to_bed",            "Hours between last meal and bedtime",              "3"),
    ("eating_window_hours",              "Length of eating window (hours)",                  "12"),
    ("screen_time_before_bed_minutes",   "Minutes of screen time in the hour before bed",    "0"),
    ("rmssd_ms",                         "RMSSD in ms (blank if unknown)",                   ""),
    ("resting_hr_bpm",                   "Resting heart rate in bpm (blank if unknown)",     ""),
    ("baseline_sleep_score",             "Your usual baseline sleep score (0 to 100)",       "75"),
    ("user_id",                          "User ID for Bayesian personalization (blank for defaults)", ""),
]


BOOL_FIELDS = {"weekend"}
OPTIONAL_FIELDS = {"alcohol_last_drink_time", "bedtime_hours", "rmssd_ms",
                   "resting_hr_bpm", "user_id"}
INT_FIELDS: set[str] = set()
STR_FIELDS = {"user_id"}


def _parse_field(field: str, raw: str) -> Any:
    """Convert a raw answer string into the correct Python type for PredictRequest."""
    raw = raw.strip()
    if raw == "":
        if field in OPTIONAL_FIELDS:
            return None
        raise ValueError(f"{field} is required")
    if field in BOOL_FIELDS:
        return raw.lower() in {"y", "yes", "true", "1"}
    if field in STR_FIELDS:
        return raw
    return float(raw)


def prompt_user() -> Dict[str, Any]:
    """Walk through every PredictRequest field, prompting for a value."""
    values: Dict[str, Any] = {}
    print("Sleep Score Simulator (CLI)")
    print("Press Enter to accept the default in square brackets.\n")
    for field, label, default in PROMPTS:
        default_display = f"[{default}]" if default != "" else "[skip]"
        prompt = f"  {label} {default_display}: "
        try:
            raw = input(prompt)
        except EOFError:
            raw = ""
        if raw.strip() == "":
            raw = default
        try:
            parsed = _parse_field(field, raw)
        except ValueError as exc:
            print(f"    could not parse {field!r}: {exc}. Using default.", file=sys.stderr)
            parsed = _parse_field(field, default) if default else None
        if parsed is not None:
            values[field] = parsed
    return values


def load_input_file(path: Path) -> Dict[str, Any]:
    """Load a JSON file whose top-level keys match PredictRequest fields."""
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object at the top level.")
    return data


def default_values() -> Dict[str, Any]:
    """Return a minimal payload that exercises every pathway at its default."""
    out: Dict[str, Any] = {}
    for field, _label, default in PROMPTS:
        if default == "":
            continue
        out[field] = _parse_field(field, default)
    return out


def print_result(req: PredictRequest, score: float, components: Dict[str, float],
                 breakdown, model_info: Dict[str, str]) -> None:
    print()
    print("=" * 68)
    print(f"  Composite sleep score:  {score:5.1f} / 100")
    print("=" * 68)

    component_caps = {"Duration": 30, "Quality": 30, "Timing": 20, "Alertness": 20}
    print("\n  Component scores:")
    for name, cap in component_caps.items():
        got = components.get(name, 0.0)
        bar = "#" * int(round(got / cap * 20))
        print(f"    {name:<10} {got:5.1f} / {cap:<2}  [{bar:<20}]")

    print("\n  Per-pathway breakdown:")
    for item in breakdown:
        sign = "+" if item.delta > 0 else ""
        print(f"    {item.label:<22} delta={sign}{item.delta:5.1f}  {item.details}")

    print("\n  Model info:")
    for k, v in model_info.items():
        print(f"    {k:<10}: {v}")
    print()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Interactive sleep-score predictor (CLI twin of /api/predict).",
    )
    p.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional JSON file with PredictRequest fields. Skips interactive prompts.",
    )
    p.add_argument(
        "--defaults",
        action="store_true",
        help="Skip prompts and run with the default payload.",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.input is not None:
        values = load_input_file(args.input)
    elif args.defaults:
        values = default_values()
    else:
        values = prompt_user()

    req = PredictRequest(**values)
    score, components, breakdown, model_info = score_sleep(req)
    print_result(req, score, components, breakdown, model_info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
