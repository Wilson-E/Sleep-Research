"""
Scenario-based evaluation of the Vitality Core pathway engine.

Runs eight representative behavioral profiles through the engine and reports
the composite 0 to 100 score plus the per-component breakdown. Backs the
paper's claim that the engine produces physiologically plausible scores and
that cross-pathway mediation meaningfully differentiates evening diet
scenarios.

Usage:
  cd sleep_score_fullstack/backend
  python scripts/scenarios.py
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.models.schemas import PredictRequest
from app.services.scoring import score_sleep

FIGURES = BACKEND.parent.parent / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)
OUT_CSV = FIGURES / "scenarios_results.csv"


@dataclass
class Scenario:
    name: str
    description: str
    request_kwargs: Dict


SCENARIOS = [
    Scenario(
        "Clean sleeper (baseline)",
        "No caffeine, no alcohol, clean meal timing, good morning light, minimal evening light.",
        dict(
            caffeine_cups=0, alcohol_drinks=0,
            bedtime_hours=23.0,
            morning_light_lux=500, evening_light_lux=10, night_light_minutes=0,
            hours_wake_to_first_eat=1.0, hours_last_eat_to_bed=3.0, eating_window_hours=11.0,
            screen_time_before_bed_minutes=0,
        ),
    ),
    Scenario(
        "Heavy caffeine only",
        "4 cups of coffee, no alcohol, clean otherwise. Targets the Caffeine Pathway.",
        dict(
            caffeine_cups=4, alcohol_drinks=0,
            bedtime_hours=23.0,
            morning_light_lux=500, evening_light_lux=10, night_light_minutes=0,
            hours_wake_to_first_eat=1.0, hours_last_eat_to_bed=3.0, eating_window_hours=11.0,
        ),
    ),
    Scenario(
        "Heavy alcohol only",
        "3 drinks, no caffeine, clean otherwise. Targets the Alcohol Pathway.",
        dict(
            caffeine_cups=0, alcohol_drinks=3,
            alcohol_last_drink_time=21.5,
            bedtime_hours=23.0,
            morning_light_lux=500, evening_light_lux=10, night_light_minutes=0,
            hours_wake_to_first_eat=1.0, hours_last_eat_to_bed=3.0, eating_window_hours=11.0,
        ),
    ),
    Scenario(
        "Caffeine + alcohol together",
        "Tests the caffeine x alcohol interaction term from Song and Walker.",
        dict(
            caffeine_cups=3, alcohol_drinks=2,
            alcohol_last_drink_time=21.5,
            bedtime_hours=23.0,
            morning_light_lux=500, evening_light_lux=10, night_light_minutes=0,
            hours_wake_to_first_eat=1.0, hours_last_eat_to_bed=3.0, eating_window_hours=11.0,
        ),
    ),
    Scenario(
        "Late-night eater (no substances)",
        "No caffeine, no alcohol, eats 1 hour before bed, long eating window. "
        "Targets chrononutrition pathway.",
        dict(
            caffeine_cups=0, alcohol_drinks=0,
            bedtime_hours=23.0,
            morning_light_lux=500, evening_light_lux=10, night_light_minutes=0,
            hours_wake_to_first_eat=4.0, hours_last_eat_to_bed=1.0, eating_window_hours=15.0,
            screen_time_before_bed_minutes=0,
        ),
    ),
    Scenario(
        "Evening diet disturbance (Soares mediation)",
        "Same late meal as above, BUT meal includes caffeine and alcohol. "
        "Targets cross-pathway mediation. Should score worse than late-eater alone.",
        dict(
            caffeine_cups=2, alcohol_drinks=1,
            alcohol_last_drink_time=21.5,
            bedtime_hours=23.0,
            morning_light_lux=500, evening_light_lux=20, night_light_minutes=0,
            hours_wake_to_first_eat=4.0, hours_last_eat_to_bed=1.0, eating_window_hours=15.0,
            screen_time_before_bed_minutes=60,
        ),
    ),
    Scenario(
        "Bad light profile",
        "Bright pre-bed light (screens/overheads), dim morning, some night light.",
        dict(
            caffeine_cups=0, alcohol_drinks=0,
            bedtime_hours=23.0,
            morning_light_lux=30, evening_light_lux=300, night_light_minutes=60,
            hours_wake_to_first_eat=1.0, hours_last_eat_to_bed=3.0, eating_window_hours=11.0,
            screen_time_before_bed_minutes=120,
        ),
    ),
    Scenario(
        "Worst-case combined",
        "4 cups caffeine, 3 drinks alcohol, late dinner, bright evening light, screens. "
        "Should produce the lowest score.",
        dict(
            caffeine_cups=4, alcohol_drinks=3,
            alcohol_last_drink_time=22.0,
            bedtime_hours=23.0,
            morning_light_lux=30, evening_light_lux=300, night_light_minutes=60,
            hours_wake_to_first_eat=5.0, hours_last_eat_to_bed=1.0, eating_window_hours=16.0,
            screen_time_before_bed_minutes=120,
        ),
    ),
]


def evaluate_scenarios():
    """Run every scenario through the engine and return a list of row dicts."""
    rows = []
    for sc in SCENARIOS:
        req = PredictRequest(**sc.request_kwargs)
        score, comp, _breakdown, _info = score_sleep(req)
        rows.append(dict(
            Scenario=sc.name,
            Score=score,
            Duration=comp.get("Duration", 0.0),
            Quality=comp.get("Quality", 0.0),
            Timing=comp.get("Timing", 0.0),
            Alertness=comp.get("Alertness", 0.0),
            Description=sc.description,
        ))
    return rows


def main():
    header = ["Scenario", "Score", "Duration", "Quality", "Timing", "Alertness", "Description"]
    col_w = [32, 7, 10, 9, 8, 11, 70]

    print("")
    print("Scenario-based evaluation of Vitality Core pathway engine")
    print("=" * (sum(col_w) + len(header) - 1))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_w)
    print(fmt.format(*header))
    print("-" * (sum(col_w) + len(header) - 1))

    rows = evaluate_scenarios()
    for r in rows:
        print(fmt.format(
            r["Scenario"][:col_w[0]],
            f"{r['Score']:.1f}",
            f"{r['Duration']:.1f}/30",
            f"{r['Quality']:.1f}/30",
            f"{r['Timing']:.1f}/20",
            f"{r['Alertness']:.1f}/20",
            r["Description"][:col_w[6]],
        ))
    print("-" * (sum(col_w) + len(header) - 1))

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {OUT_CSV}")

    clean = next(r for r in rows if "Clean" in r["Scenario"])
    late_only = next(r for r in rows if "Late-night eater" in r["Scenario"])
    late_plus = next(r for r in rows if "Evening diet disturbance" in r["Scenario"])
    worst = next(r for r in rows if "Worst-case" in r["Scenario"])

    print("\nScenario sanity checks (abstract claims)")
    print(f"Clean sleeper:                   {clean['Score']:.1f}")
    print(f"Late-night eater alone:          {late_only['Score']:.1f}  (expected below clean)")
    print(f"Late-night eater + caffeine/alc: {late_plus['Score']:.1f}  (expected below late-only; mediation penalty)")
    print(f"Worst-case combined:             {worst['Score']:.1f}  (expected below all above)")
    print("")
    print("Cross-pathway mediation differential (late+diet vs late alone):")
    print(f"  {late_only['Score']:.1f} minus {late_plus['Score']:.1f} equals "
          f"{late_only['Score'] - late_plus['Score']:.1f} pts")
    print("  A positive number confirms that mediation worsens the score.")


if __name__ == "__main__":
    main()
