"""
sleep_log.py
============
File-based sleep log storage system.
Each user's log is stored as a JSON file in the configured log directory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SleepLogEntry:
    """A single night's logged data: inputs + observed outcome."""

    date: str                               # ISO date "YYYY-MM-DD"
    timestamp: str                          # ISO datetime when logged

    # Inputs stored for replay / Bayesian updating
    caffeine_doses: List[Dict]              # [{"time": 8.0, "mg": 95.0}, ...]
    alcohol_drinks: float
    morning_light_lux: float
    evening_light_lux: float
    night_light_minutes: float
    hours_wake_to_first_eat: float
    hours_last_eat_to_bed: float
    eating_window_hours: float
    bedtime_hours: float
    screen_time_before_bed_minutes: float
    weekend: bool

    # Predicted score (what the engine said BEFORE the night)
    predicted_score: float
    predicted_components: Dict[str, float]

    # Optional inputs
    alcohol_last_drink_time: Optional[float] = None

    # Observed outcomes (logged the next morning)
    observed_sleep_duration_hours: Optional[float] = None
    observed_sleep_quality_subjective: Optional[int] = None
    observed_sleep_onset_latency_minutes: Optional[float] = None
    observed_awakenings: Optional[int] = None
    observed_morning_alertness: Optional[int] = None

    # Derived observed composite score
    observed_score: Optional[float] = None


# ---------------------------------------------------------------------------
# Observed-to-score conversion
# ---------------------------------------------------------------------------

def compute_observed_score(
    duration_hours: Optional[float],
    quality_subjective: Optional[int],
    onset_latency_minutes: Optional[float],
    awakenings: Optional[int],
    morning_alertness: Optional[int],
) -> Optional[float]:
    """
    Maps observed sleep outcomes to a 0-100 composite score comparable to
    the predicted score from the simulation engine.

    Weights align with the four engine components:
      Duration   (max 30): 7-9h optimal
      Quality    (max 30): maps from 1-5 subjective rating
      Timing     (max 20): onset latency <15 min optimal
      Alertness  (max 20): maps from 1-5 morning alertness

    Returns None if insufficient data (need at least duration + quality).
    """
    if duration_hours is None or quality_subjective is None:
        return None

    # Duration component (0-30)
    if 7.0 <= duration_hours <= 9.0:
        dur_score = 30.0
    elif duration_hours < 7.0:
        dur_score = max(0.0, 30.0 - (7.0 - duration_hours) * 8.0)
    else:
        dur_score = max(0.0, 30.0 - (duration_hours - 9.0) * 5.0)

    # Quality component (0-30): map 1-5 to 0-30
    qual_score = (quality_subjective - 1) / 4.0 * 30.0

    # Timing/Latency component (0-20)
    if onset_latency_minutes is not None:
        if onset_latency_minutes <= 15:
            lat_score = 20.0
        else:
            lat_score = max(0.0, 20.0 - (onset_latency_minutes - 15) * 0.5)
    else:
        lat_score = 12.0  # neutral default

    # Alertness component (0-20): map 1-5 to 0-20
    if morning_alertness is not None:
        alert_score = (morning_alertness - 1) / 4.0 * 20.0
    else:
        alert_score = 10.0  # neutral default

    return round(_clamp(dur_score + qual_score + lat_score + alert_score, 0.0, 100.0), 1)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class SleepLogStore:
    """File-based sleep log storage. One JSON file per user."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _user_path(self, user_id: str) -> Path:
        safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
        return self.storage_dir / f"{safe_id}.json"

    def get_entries(self, user_id: str) -> List[SleepLogEntry]:
        path = self._user_path(user_id)
        if not path.exists():
            return []
        with path.open() as f:
            data = json.load(f)
        return [SleepLogEntry(**entry) for entry in data.get("entries", [])]

    def add_entry(self, user_id: str, entry: SleepLogEntry) -> None:
        entries = self.get_entries(user_id)
        # Replace if date already exists (idempotent re-log)
        entries = [e for e in entries if e.date != entry.date]
        entries.append(entry)
        self._save(user_id, entries)

    def update_entry_observed(self, user_id: str, date: str, observed: Dict) -> Optional[SleepLogEntry]:
        """Update an existing entry's observed outcomes (morning-after logging).

        Returns the updated entry, or None if no entry found for that date.
        """
        entries = self.get_entries(user_id)
        updated = None
        for entry in entries:
            if entry.date == date:
                for key, value in observed.items():
                    if hasattr(entry, key) and value is not None:
                        setattr(entry, key, value)
                entry.observed_score = compute_observed_score(
                    entry.observed_sleep_duration_hours,
                    entry.observed_sleep_quality_subjective,
                    entry.observed_sleep_onset_latency_minutes,
                    entry.observed_awakenings,
                    entry.observed_morning_alertness,
                )
                updated = entry
                break
        if updated is not None:
            self._save(user_id, entries)
        return updated

    def _save(self, user_id: str, entries: List[SleepLogEntry]) -> None:
        path = self._user_path(user_id)
        data = {"entries": [asdict(entry) for entry in entries]}
        with path.open("w") as f:
            json.dump(data, f, indent=2)
