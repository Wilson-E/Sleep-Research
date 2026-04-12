"""
data_harmonizer.py
==================
Combines three data sources into a common schema for model training
and validation:

1. Financial traders (Song & Walker 2023) - 552 rows, 17 participants
2. Didikoglu et al. (2023) PNAS - 478 rows, 59 participants
3. NHANES 2017-2020 pre-pandemic - ~5,000+ rows, one per participant

Common output columns:
    participant_id       str     Unique participant identifier (prefixed by source)
    caffeine_units       float   Cups of coffee equivalent
    alcohol_units        float   Standard drinks
    sleep_duration_hours float   Hours of sleep
    sleep_quality_score  float   Subjective quality 0-100 (higher = better)
    is_weekend           float   1.0 = weekend/free day, 0.0 = weekday/work
    bedtime_hours        float   Hours past midnight (e.g., 23.0 = 11 PM)
    dataset_source       str     "traders", "didikoglu", or "nhanes"
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.services.nhanes_loader import load_nhanes

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Traders dataset
# ---------------------------------------------------------------------------

def _parse_traders_time(time_str: str) -> float:
    """Parse '10:00 PM' or '2:30 AM' to fractional hours past midnight."""
    try:
        time_str = time_str.strip()
        parts = time_str.split()
        if len(parts) != 2:
            return np.nan
        hhmm, ampm = parts[0], parts[1].upper()
        h, m = hhmm.split(":")
        h, m = int(h), int(m)
        if ampm == "PM" and h != 12:
            h += 12
        elif ampm == "AM" and h == 12:
            h = 0
        return h + m / 60.0
    except Exception:
        return np.nan


def load_traders(data_dir: Path) -> pd.DataFrame:
    """Load and harmonize the financial traders dataset."""
    path = data_dir / "financial_traders_data.csv"
    df = pd.read_csv(path)

    result = pd.DataFrame()
    result["participant_id"] = "traders_" + df["ParticipantID"].astype(str)
    result["caffeine_units"] = pd.to_numeric(df["Caffeine"], errors="coerce")
    result["alcohol_units"] = pd.to_numeric(df["Alcohol"], errors="coerce")
    result["sleep_duration_hours"] = pd.to_numeric(df["Duration"], errors="coerce") / 60.0
    result["sleep_quality_score"] = pd.to_numeric(df["SSQ"], errors="coerce")
    result["is_weekend"] = pd.to_numeric(df["Weekend"], errors="coerce")
    result["bedtime_hours"] = df["BedTime"].apply(_parse_traders_time)
    result["dataset_source"] = "traders"

    # Drop rows missing key variables
    result.dropna(subset=["caffeine_units", "alcohol_units",
                          "sleep_duration_hours", "sleep_quality_score"],
                  inplace=True)
    result.reset_index(drop=True, inplace=True)

    log.info("Traders dataset: %d rows", len(result))
    return result


# ---------------------------------------------------------------------------
# 2. Didikoglu dataset
# ---------------------------------------------------------------------------

# Map categorical sleep quality to 0-100 numeric scale.
# Anchored to approximate the traders SSQ distribution:
#   traders SSQ mean ~72, sd ~14; mapping chosen so
#   Good (most frequent in Didikoglu) maps near the traders mean.
_QUALITY_MAP = {
    "VeryGood": 90.0,
    "Good": 70.0,
    "Fair": 50.0,
    "Bad": 30.0,
    "VeryBad": 10.0,
}


def _didikoglu_bedtime(offset: float) -> float:
    """Convert Didikoglu bedtime offset to hours past midnight.

    In their coding: negative values = hours before midnight,
    positive = hours after midnight.
    e.g., -1.0 means 23:00 (11 PM), 1.5 means 01:30 (1:30 AM).
    """
    if np.isnan(offset):
        return np.nan
    if offset < 0:
        return 24.0 + offset  # -1 -> 23, -2 -> 22
    return offset  # 1.5 -> 1.5 (1:30 AM)


def load_didikoglu(data_dir: Path) -> pd.DataFrame:
    """Load and harmonize the Didikoglu et al. PNAS dataset."""
    path = data_dir / "Didikoglu_et_al_2023_PNAS_sleep.csv"
    df = pd.read_csv(path)

    result = pd.DataFrame()
    result["participant_id"] = "didikoglu_" + df["id"].astype(str)
    result["caffeine_units"] = pd.to_numeric(df["caffeineYesterdayUnit"], errors="coerce")
    result["alcohol_units"] = pd.to_numeric(df["alcoholYesterdayUnit"], errors="coerce")
    result["sleep_duration_hours"] = pd.to_numeric(df["sleepDurationYesterday"], errors="coerce")
    result["sleep_quality_score"] = df["sleepQualitySubjRateYesterday"].map(_QUALITY_MAP)

    # Weekend: Free -> 1, Work -> 0
    result["is_weekend"] = df["workdayYesterday"].map({"Free": 1.0, "Work": 0.0})

    result["bedtime_hours"] = pd.to_numeric(df["gobedTimeYesterday"], errors="coerce").apply(
        _didikoglu_bedtime
    )
    result["dataset_source"] = "didikoglu"

    # Drop rows missing key variables
    result.dropna(subset=["caffeine_units", "sleep_duration_hours",
                          "sleep_quality_score"], inplace=True)
    result.reset_index(drop=True, inplace=True)

    log.info("Didikoglu dataset: %d rows", len(result))
    return result


# ---------------------------------------------------------------------------
# 3. NHANES dataset
# ---------------------------------------------------------------------------

def _nhanes_quality_score(sleepiness: float, trouble: float, duration: float) -> float:
    """Construct a 0-100 sleep quality proxy from NHANES variables.

    Components (each on 0-100, then averaged):
      1. Sleepiness (SLQ120): 0=never sleepy -> 100, 4=always sleepy -> 0
      2. Trouble sleeping (SLQ050): No trouble -> 80, trouble -> 30
      3. Duration adequacy: 7-9h -> 100, penalty outside that range

    Higher score = better sleep quality (consistent with traders SSQ).
    """
    # Sleepiness component (0-4 scale inverted to 0-100)
    if np.isnan(sleepiness):
        sleepiness_score = 60.0  # neutral default
    else:
        sleepiness_score = max(0.0, 100.0 - sleepiness * 25.0)

    # Trouble sleeping component
    if np.isnan(trouble):
        trouble_score = 60.0
    else:
        trouble_score = 80.0 if trouble == 0 else 30.0

    # Duration adequacy component
    if np.isnan(duration):
        duration_score = 60.0
    else:
        if 7.0 <= duration <= 9.0:
            duration_score = 100.0
        elif duration < 7.0:
            duration_score = max(0.0, 100.0 - (7.0 - duration) * 20.0)
        else:
            duration_score = max(0.0, 100.0 - (duration - 9.0) * 15.0)

    return (sleepiness_score + trouble_score + duration_score) / 3.0


def load_nhanes_harmonized(data_dir: Path) -> Optional[pd.DataFrame]:
    """Load NHANES and harmonize to common schema."""
    nhanes = load_nhanes(data_dir)
    if nhanes is None:
        return None

    result = pd.DataFrame()
    result["participant_id"] = "nhanes_" + nhanes["participant_id"]
    result["caffeine_units"] = nhanes["caffeine_cups"]
    result["alcohol_units"] = nhanes["alcohol_drinks"]
    result["sleep_duration_hours"] = nhanes["sleep_duration_hours"]

    # Construct composite quality score from sleepiness + trouble + duration
    result["sleep_quality_score"] = [
        _nhanes_quality_score(s, t, d)
        for s, t, d in zip(
            nhanes["sleepiness_scale"],
            nhanes["trouble_sleeping"],
            nhanes["sleep_duration_hours"],
        )
    ]

    # NHANES doesn't distinguish weekend in the sleep questionnaire
    # (SLD012 is "usual weekday" duration). Set to 0.0 (weekday assumption).
    result["is_weekend"] = 0.0

    result["bedtime_hours"] = nhanes["bedtime_hours"]
    result["dataset_source"] = "nhanes"

    result.dropna(subset=["caffeine_units", "sleep_duration_hours",
                          "sleep_quality_score"], inplace=True)
    result.reset_index(drop=True, inplace=True)

    log.info("NHANES harmonized: %d rows", len(result))
    return result


# ---------------------------------------------------------------------------
# Combined harmonized dataset
# ---------------------------------------------------------------------------

def load_harmonized(data_dir: Path) -> pd.DataFrame:
    """Load and combine all three data sources into a single DataFrame.

    Returns a DataFrame with the common schema columns, ready for
    model training and validation.
    """
    traders = load_traders(data_dir)
    didikoglu = load_didikoglu(data_dir)
    nhanes = load_nhanes_harmonized(data_dir)

    frames = [traders, didikoglu]
    if nhanes is not None:
        frames.append(nhanes)
    else:
        log.warning("NHANES data not available; proceeding with traders + Didikoglu only")

    combined = pd.concat(frames, ignore_index=True)

    log.info(
        "Combined harmonized dataset: %d rows (%s)",
        len(combined),
        ", ".join(f"{src}={n}" for src, n in combined["dataset_source"].value_counts().items()),
    )

    return combined
