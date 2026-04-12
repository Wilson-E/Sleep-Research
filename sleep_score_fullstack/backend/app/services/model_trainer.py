"""
model_trainer.py
================
Trains four model tiers on the harmonized sleep dataset:

  A. Calibrated Pathway Coefficients — learns the pathway engine's key
     parameters from data via constrained optimization.
  B. OLS Multiple Regression — statsmodels with full inference tables.
  C. SEM Path Analysis — semopy structural equation model inspired by
     Soares et al. (2025), testing mediation effects.
  D. Random Forest — sklearn benchmark for predictive ceiling.

All models predict sleep_quality_score (0-100) from lifestyle factors.
A secondary target (sleep_duration_hours) is also modeled where appropriate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.ensemble import RandomForestRegressor

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build the common feature matrix from harmonized data.

    Returns a DataFrame with columns:
        caffeine, alcohol, caf_x_alc, is_weekend, bedtime
    Rows with any NaN in these columns are dropped.
    """
    features = pd.DataFrame()
    features["caffeine"] = df["caffeine_units"]
    features["alcohol"] = df["alcohol_units"]
    features["caf_x_alc"] = df["caffeine_units"] * df["alcohol_units"]
    features["is_weekend"] = df["is_weekend"]
    features["bedtime"] = df["bedtime_hours"]
    features["sleep_duration"] = df["sleep_duration_hours"]
    features["quality"] = df["sleep_quality_score"]
    features.dropna(inplace=True)
    return features


# ---------------------------------------------------------------------------
# Model A: Calibrated Pathway Coefficients
# ---------------------------------------------------------------------------

@dataclass
class CalibratedCoefficients:
    """Coefficients learned from data for the pathway engine."""
    minutes_lost_per_cup: float = 10.4       # literature default
    quality_pen_per_drink: float = 3.04      # literature default
    interaction_coeff: float = 1.29          # literature default
    literature_values: Dict[str, float] = field(default_factory=lambda: {
        "minutes_lost_per_cup": 10.4,
        "quality_pen_per_drink": 3.04,
        "interaction_coeff": 1.29,
    })
    n_observations: int = 0
    optimization_success: bool = False


def train_calibrated_pathways(df: pd.DataFrame) -> CalibratedCoefficients:
    """Learn pathway coefficients by minimizing prediction error.

    Uses the same functional form as the pathway engine:
      duration_penalty = caffeine * minutes_lost_per_cup
      quality_penalty  = alcohol * quality_pen_per_drink
                       - caffeine * alcohol * interaction_coeff
      predicted_quality = baseline - quality_penalty - (duration_penalty / 60) * k

    The optimization finds coefficients that minimize MSE of predicted
    vs. observed sleep quality scores.
    """
    feat = _prepare_features(df)
    if len(feat) < 20:
        log.warning("Too few rows for pathway calibration: %d", len(feat))
        return CalibratedCoefficients()

    caffeine = feat["caffeine"].values
    alcohol = feat["alcohol"].values
    quality = feat["quality"].values
    n = len(feat)

    # Baseline quality: mean quality when caffeine=0 and alcohol=0
    no_substance = feat[(feat["caffeine"] < 0.5) & (feat["alcohol"] < 0.5)]
    if len(no_substance) > 10:
        baseline = no_substance["quality"].mean()
    else:
        baseline = quality.mean()

    def objective(params):
        min_per_cup, qual_per_drink, interact = params
        # Quality penalty from alcohol
        alc_pen = alcohol * qual_per_drink
        # Interaction offset (caffeine partially masks alcohol)
        interact_offset = caffeine * alcohol * interact
        # Duration penalty converted to quality impact (10 min lost ~ 2 quality pts)
        dur_pen = caffeine * min_per_cup * (2.0 / 60.0)
        predicted = baseline - alc_pen + interact_offset - dur_pen
        residuals = quality - predicted
        return np.mean(residuals ** 2)

    # Constrained optimization: all coefficients must be non-negative
    result = minimize(
        objective,
        x0=[10.4, 3.04, 1.29],  # start from literature values
        bounds=[(0.0, 50.0), (0.0, 20.0), (0.0, 10.0)],
        method="L-BFGS-B",
    )

    coefs = CalibratedCoefficients(
        minutes_lost_per_cup=round(result.x[0], 2),
        quality_pen_per_drink=round(result.x[1], 2),
        interaction_coeff=round(result.x[2], 2),
        n_observations=n,
        optimization_success=result.success,
    )

    log.info(
        "Calibrated coefficients: min/cup=%.2f (lit=10.4), qual/drink=%.2f (lit=3.04), "
        "interact=%.2f (lit=1.29), n=%d, success=%s",
        coefs.minutes_lost_per_cup, coefs.quality_pen_per_drink,
        coefs.interaction_coeff, n, result.success,
    )
    return coefs


# ---------------------------------------------------------------------------
# Model B: OLS Multiple Regression
# ---------------------------------------------------------------------------

@dataclass
class OLSResults:
    """Results from OLS regression with full inference."""
    # Quality model
    quality_summary: str = ""
    quality_r_squared: float = 0.0
    quality_adj_r_squared: float = 0.0
    quality_f_pvalue: float = 1.0
    quality_coefficients: Dict[str, Dict[str, float]] = field(default_factory=dict)
    quality_vif: Dict[str, float] = field(default_factory=dict)
    # Duration model
    duration_summary: str = ""
    duration_r_squared: float = 0.0
    duration_adj_r_squared: float = 0.0
    duration_coefficients: Dict[str, Dict[str, float]] = field(default_factory=dict)
    n_observations: int = 0
    # Fitted model objects for prediction
    quality_model: Any = None
    duration_model: Any = None


def train_ols_regression(df: pd.DataFrame) -> OLSResults:
    """Train OLS regression with full statistical inference."""
    feat = _prepare_features(df)
    if len(feat) < 20:
        log.warning("Too few rows for OLS: %d", len(feat))
        return OLSResults()

    X_cols = ["caffeine", "alcohol", "caf_x_alc", "is_weekend"]
    X = feat[X_cols].copy()
    X_const = sm.add_constant(X)

    results = OLSResults(n_observations=len(feat))

    # Quality model
    y_qual = feat["quality"]
    qual_model = sm.OLS(y_qual, X_const).fit()
    results.quality_summary = qual_model.summary().as_text()
    results.quality_r_squared = round(qual_model.rsquared, 4)
    results.quality_adj_r_squared = round(qual_model.rsquared_adj, 4)
    results.quality_f_pvalue = round(qual_model.f_pvalue, 6)
    results.quality_model = qual_model

    for name in qual_model.params.index:
        results.quality_coefficients[name] = {
            "coef": round(qual_model.params[name], 4),
            "se": round(qual_model.bse[name], 4),
            "t": round(qual_model.tvalues[name], 4),
            "p": round(qual_model.pvalues[name], 6),
            "ci_lower": round(qual_model.conf_int().loc[name, 0], 4),
            "ci_upper": round(qual_model.conf_int().loc[name, 1], 4),
        }

    # VIF for multicollinearity
    for i, col in enumerate(X_cols):
        vif = variance_inflation_factor(X.values, i)
        results.quality_vif[col] = round(vif, 2)

    # Duration model
    y_dur = feat["sleep_duration"]
    dur_model = sm.OLS(y_dur, X_const).fit()
    results.duration_summary = dur_model.summary().as_text()
    results.duration_r_squared = round(dur_model.rsquared, 4)
    results.duration_adj_r_squared = round(dur_model.rsquared_adj, 4)
    results.duration_model = dur_model

    for name in dur_model.params.index:
        results.duration_coefficients[name] = {
            "coef": round(dur_model.params[name], 4),
            "se": round(dur_model.bse[name], 4),
            "t": round(dur_model.tvalues[name], 4),
            "p": round(dur_model.pvalues[name], 6),
        }

    log.info(
        "OLS quality: R^2=%.4f, adj R^2=%.4f, F p=%.2e | duration: R^2=%.4f",
        results.quality_r_squared, results.quality_adj_r_squared,
        results.quality_f_pvalue, results.duration_r_squared,
    )
    return results


# ---------------------------------------------------------------------------
# Model C: SEM Path Analysis (Soares-inspired)
# ---------------------------------------------------------------------------

@dataclass
class SEMResults:
    """Results from Structural Equation Modeling."""
    model_description: str = ""
    path_coefficients: Dict[str, Dict[str, float]] = field(default_factory=dict)
    fit_indices: Dict[str, float] = field(default_factory=dict)
    direct_effects: Dict[str, float] = field(default_factory=dict)
    indirect_effects: Dict[str, float] = field(default_factory=dict)
    n_observations: int = 0
    converged: bool = False


def train_sem_path_model(df: pd.DataFrame) -> SEMResults:
    """Train SEM path model inspired by Soares et al. (2025).

    Tests mediation: caffeine/alcohol -> sleep_duration -> sleep_quality.

    Path diagram:
        caffeine  ---(a1)---> sleep_duration ---(b)---> sleep_quality
        alcohol   ---(a2)---> sleep_duration
        caffeine  ---(c1)---> sleep_quality   (direct effect)
        alcohol   ---(c2)---> sleep_quality   (direct effect)
        is_weekend ---> sleep_duration, sleep_quality
    """
    try:
        from semopy import Model as SEMModel
    except ImportError:
        log.warning("semopy not installed; skipping SEM model")
        return SEMResults(model_description="semopy not available")

    feat = _prepare_features(df)
    if len(feat) < 50:
        log.warning("Too few rows for SEM: %d", len(feat))
        return SEMResults()

    results = SEMResults(n_observations=len(feat))

    # Lavaan-style model specification
    model_spec = """
    sleep_duration ~ caffeine + alcohol + is_weekend + bedtime
    quality ~ caffeine + alcohol + sleep_duration + is_weekend
    """
    results.model_description = model_spec.strip()

    try:
        sem = SEMModel(model_spec)
        sem.fit(feat)
        results.converged = True

        # Extract parameter estimates
        estimates = sem.inspect()
        for _, row in estimates.iterrows():
            key = f"{row['lval']} ~ {row['rval']}"
            results.path_coefficients[key] = {
                "estimate": round(float(row["Estimate"]), 4),
                "std_err": round(float(row.get("Std. Err", 0)), 4),
                "z": round(float(row.get("z-value", 0)), 4),
                "p": round(float(row.get("p-value", 1)), 6),
            }

        # Compute fit indices using module-level calc_stats
        try:
            import semopy
            stats_df = semopy.calc_stats(sem)
            # stats_df is a DataFrame with one row; extract values
            for col in stats_df.columns:
                val = stats_df[col].iloc[0]
                if isinstance(val, (int, float)) and not np.isnan(val):
                    results.fit_indices[col] = round(float(val), 4)
        except Exception as e:
            log.warning("Could not compute SEM fit indices: %s", e)

        # Extract direct and indirect effects for mediation analysis
        # Direct: caffeine -> quality, alcohol -> quality
        # Indirect: caffeine -> duration -> quality, alcohol -> duration -> quality
        for _, row in estimates.iterrows():
            lval, rval = row["lval"], row["rval"]
            est = float(row["Estimate"])
            if lval == "quality" and rval in ("caffeine", "alcohol"):
                results.direct_effects[f"{rval} -> quality"] = round(est, 4)
            if lval == "sleep_duration" and rval in ("caffeine", "alcohol"):
                results.direct_effects[f"{rval} -> duration"] = round(est, 4)
            if lval == "quality" and rval == "sleep_duration":
                results.direct_effects["duration -> quality"] = round(est, 4)

        # Indirect effect = a * b (product of path coefficients)
        b = results.direct_effects.get("duration -> quality", 0)
        for substance in ["caffeine", "alcohol"]:
            a = results.direct_effects.get(f"{substance} -> duration", 0)
            results.indirect_effects[f"{substance} -> duration -> quality"] = round(a * b, 4)

        log.info(
            "SEM converged: %d paths, direct effects: %s, indirect effects: %s",
            len(results.path_coefficients), results.direct_effects, results.indirect_effects,
        )

    except Exception as e:
        log.error("SEM model failed: %s", e)
        results.converged = False

    return results


# ---------------------------------------------------------------------------
# Model D: Random Forest Benchmark
# ---------------------------------------------------------------------------

@dataclass
class RandomForestResults:
    """Results from Random Forest regression."""
    feature_importances: Dict[str, float] = field(default_factory=dict)
    n_observations: int = 0
    n_estimators: int = 100
    max_depth: int = 5
    oob_score: Optional[float] = None
    model: Any = None  # fitted RandomForestRegressor


def train_random_forest(df: pd.DataFrame) -> RandomForestResults:
    """Train Random Forest as a predictive benchmark."""
    feat = _prepare_features(df)
    if len(feat) < 20:
        log.warning("Too few rows for RF: %d", len(feat))
        return RandomForestResults()

    X_cols = ["caffeine", "alcohol", "caf_x_alc", "is_weekend", "bedtime", "sleep_duration"]
    X = feat[X_cols].values
    y = feat["quality"].values

    rf = RandomForestRegressor(
        n_estimators=100,
        max_depth=5,
        random_state=42,
        oob_score=True,
        n_jobs=-1,
    )
    rf.fit(X, y)

    results = RandomForestResults(
        n_observations=len(feat),
        n_estimators=100,
        max_depth=5,
        oob_score=round(rf.oob_score_, 4),
        model=rf,
    )

    for col, imp in zip(X_cols, rf.feature_importances_):
        results.feature_importances[col] = round(float(imp), 4)

    log.info(
        "Random Forest: OOB R^2=%.4f, top features: %s",
        rf.oob_score_,
        sorted(results.feature_importances.items(), key=lambda x: -x[1])[:3],
    )
    return results


# ---------------------------------------------------------------------------
# Train all models
# ---------------------------------------------------------------------------

@dataclass
class AllModels:
    """Container for all trained model tiers."""
    calibrated: CalibratedCoefficients = field(default_factory=CalibratedCoefficients)
    ols: OLSResults = field(default_factory=OLSResults)
    sem: SEMResults = field(default_factory=SEMResults)
    rf: RandomForestResults = field(default_factory=RandomForestResults)
    dataset_size: int = 0
    dataset_sources: Dict[str, int] = field(default_factory=dict)


def train_all_models(df: pd.DataFrame) -> AllModels:
    """Train all four model tiers on the harmonized dataset."""
    log.info("Training all models on %d rows...", len(df))

    models = AllModels(
        dataset_size=len(df),
        dataset_sources=df["dataset_source"].value_counts().to_dict(),
    )

    models.calibrated = train_calibrated_pathways(df)
    models.ols = train_ols_regression(df)
    models.sem = train_sem_path_model(df)
    models.rf = train_random_forest(df)

    log.info("All models trained successfully.")
    return models
