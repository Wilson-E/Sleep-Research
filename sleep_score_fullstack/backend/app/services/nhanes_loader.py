"""
nhanes_loader.py
================
Reads and merges NHANES 2017-March 2020 pre-pandemic XPT files into a
clean DataFrame suitable for sleep/dietary analysis.

Required files in data/:
  - P_SLQ.xpt       (Sleep Disorders Questionnaire)
  - P_DEMO.xpt      (Demographics)
  - P_BMX.xpt       (Body Measures)
  - P_DR1TOT.xpt.txt (Total Nutrient Intakes, Day 1)

All linked via SEQN (participant sequence number).

NHANES variable reference:
  P_SLQ:
    SLQ300  - Usual weekday bedtime (HH:MM)
    SLQ310  - Usual weekday wake time (HH:MM)
    SLD012  - Weekday sleep duration (hours)
    SLQ320  - Usual weekend bedtime (HH:MM)
    SLQ330  - Usual weekend wake time (HH:MM)
    SLD013  - Weekend sleep duration (hours)
    SLQ050  - Ever told doctor had trouble sleeping (1=Yes, 2=No)
    SLQ120  - Sleepiness scale (0=never to 4=almost always; 7/9=refused/don't know)

  P_DEMO:
    RIDAGEYR - Age in years at screening
    RIAGENDR - Gender (1=Male, 2=Female)

  P_BMX:
    BMXBMI   - Body Mass Index (kg/m^2)

  P_DR1TOT:
    DR1TCAFF - Total caffeine (mg)
    DR1TALCO - Total alcohol (g)
    DR1TKCAL - Total calories (kcal)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# SAS XPT transport format uses a special sentinel for missing values
# that pandas reads as extremely small floats (~5.4e-79). We replace
# any value with absolute value < 1e-70 with NaN.
_SAS_MISSING_THRESHOLD = 1e-70


def _clean_sas_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Replace SAS transport missing value sentinels with NaN."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        mask = df[col].abs() < _SAS_MISSING_THRESHOLD
        df.loc[mask, col] = np.nan
    return df


def _parse_nhanes_time(series: pd.Series) -> pd.Series:
    """Parse NHANES time fields (bytes like b'22:00') to fractional hours past midnight."""
    def _to_hours(val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return np.nan
        try:
            s = val.decode("ascii") if isinstance(val, bytes) else str(val)
            parts = s.strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            return h + m / 60.0
        except Exception:
            return np.nan

    return series.apply(_to_hours)


def load_nhanes(data_dir: Path) -> Optional[pd.DataFrame]:
    """Load and merge NHANES files into a clean analysis DataFrame.

    Returns a DataFrame with columns:
        participant_id, caffeine_mg, alcohol_g, calories,
        sleep_duration_hours, sleepiness_scale, trouble_sleeping,
        bedtime_hours, wake_time_hours, age, gender, bmi,
        dataset_source
    """
    slq_path = data_dir / "P_SLQ.xpt"
    demo_path = data_dir / "P_DEMO.xpt"
    bmx_path = data_dir / "P_BMX.xpt"
    dr1_path = data_dir / "P_DR1TOT.xpt.txt"

    for p in [slq_path, demo_path, bmx_path, dr1_path]:
        if not p.exists():
            log.warning("NHANES file missing: %s", p)
            return None

    # Load each file
    slq = _clean_sas_missing(pd.read_sas(str(slq_path), format="xport"))
    demo = _clean_sas_missing(pd.read_sas(str(demo_path), format="xport"))
    bmx = _clean_sas_missing(pd.read_sas(str(bmx_path), format="xport"))
    dr1 = _clean_sas_missing(pd.read_sas(str(dr1_path), format="xport"))

    log.info(
        "NHANES raw sizes: SLQ=%d, DEMO=%d, BMX=%d, DR1TOT=%d",
        len(slq), len(demo), len(bmx), len(dr1),
    )

    # Parse bedtime/waketime from bytes to fractional hours
    slq["bedtime_hours"] = _parse_nhanes_time(slq["SLQ300"])
    slq["wake_time_hours"] = _parse_nhanes_time(slq["SLQ310"])

    # Clean sleepiness scale: valid values 0-4, others (7=refused, 9=don't know) -> NaN
    slq["sleepiness_scale"] = slq["SLQ120"].where(slq["SLQ120"].between(0, 4), np.nan)

    # Trouble sleeping: 1=Yes, 2=No; recode to binary (1=trouble, 0=no trouble)
    slq["trouble_sleeping"] = slq["SLQ050"].map({1.0: 1, 2.0: 0})

    slq_clean = slq[["SEQN", "SLD012", "bedtime_hours", "wake_time_hours",
                      "sleepiness_scale", "trouble_sleeping"]].copy()
    slq_clean.rename(columns={"SLD012": "sleep_duration_hours"}, inplace=True)

    # Demographics: age (16+, since SLQ is only for 16+) and gender
    demo_clean = demo[["SEQN", "RIDAGEYR", "RIAGENDR"]].copy()
    demo_clean.rename(columns={"RIDAGEYR": "age", "RIAGENDR": "gender"}, inplace=True)

    # Body measures: BMI
    bmx_clean = bmx[["SEQN", "BMXBMI"]].copy()
    bmx_clean.rename(columns={"BMXBMI": "bmi"}, inplace=True)

    # Dietary totals: caffeine (mg), alcohol (g), calories (kcal)
    dr1_clean = dr1[["SEQN", "DR1TCAFF", "DR1TALCO", "DR1TKCAL"]].copy()
    dr1_clean.rename(columns={
        "DR1TCAFF": "caffeine_mg",
        "DR1TALCO": "alcohol_g",
        "DR1TKCAL": "calories",
    }, inplace=True)

    # Merge all on SEQN
    merged = (
        slq_clean
        .merge(demo_clean, on="SEQN", how="inner")
        .merge(bmx_clean, on="SEQN", how="left")
        .merge(dr1_clean, on="SEQN", how="inner")
    )

    # Filter: adults 18-65 with valid sleep duration and caffeine data
    merged = merged[
        (merged["age"] >= 18) &
        (merged["age"] <= 65) &
        (merged["sleep_duration_hours"].notna()) &
        (merged["caffeine_mg"].notna())
    ].copy()

    # Convert units for harmonization
    merged["caffeine_cups"] = merged["caffeine_mg"] / 95.0  # 95mg per cup equivalent
    # In NHANES dietary recall, missing alcohol means no alcohol was consumed
    # (the participant's 24h recall had no alcoholic items). Treat as 0.
    merged["alcohol_g"] = merged["alcohol_g"].fillna(0.0)
    merged["alcohol_drinks"] = merged["alcohol_g"] / 14.0   # 14g per standard drink

    # Create participant_id as string
    merged["participant_id"] = merged["SEQN"].astype(int).astype(str)
    merged["dataset_source"] = "nhanes"

    # Select final columns
    result = merged[[
        "participant_id", "caffeine_cups", "caffeine_mg", "alcohol_drinks",
        "alcohol_g", "sleep_duration_hours", "sleepiness_scale",
        "trouble_sleeping", "bedtime_hours", "wake_time_hours",
        "age", "gender", "bmi", "calories", "dataset_source",
    ]].copy()

    result.reset_index(drop=True, inplace=True)
    log.info("NHANES merged dataset: %d rows, %d columns", len(result), len(result.columns))

    return result
