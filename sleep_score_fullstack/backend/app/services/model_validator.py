"""
model_validator.py
==================
Cross-validation pipeline for comparing model tiers.

Uses GroupKFold (k=5) grouped by participant_id for datasets with
repeated measures (traders, Didikoglu). For NHANES (one observation
per participant), standard KFold is equivalent.

Reports: R-squared, RMSE, MAE, Pearson r for each model and fold.
Produces a comparison table including the current hardcoded baseline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import pearsonr
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import RandomForestRegressor
import statsmodels.api as sm

log = logging.getLogger(__name__)


@dataclass
class FoldMetrics:
    """Metrics for a single CV fold."""
    r_squared: float
    rmse: float
    mae: float
    pearson_r: float
    n_train: int
    n_test: int


@dataclass
class ModelCVResults:
    """Cross-validation results for one model."""
    model_name: str
    fold_metrics: List[FoldMetrics] = field(default_factory=list)
    mean_r_squared: float = 0.0
    std_r_squared: float = 0.0
    mean_rmse: float = 0.0
    std_rmse: float = 0.0
    mean_mae: float = 0.0
    std_mae: float = 0.0
    mean_pearson_r: float = 0.0
    n_total: int = 0

    def compute_summary(self) -> None:
        if not self.fold_metrics:
            return
        r2s = [f.r_squared for f in self.fold_metrics]
        rmses = [f.rmse for f in self.fold_metrics]
        maes = [f.mae for f in self.fold_metrics]
        rs = [f.pearson_r for f in self.fold_metrics]
        self.mean_r_squared = round(float(np.mean(r2s)), 4)
        self.std_r_squared = round(float(np.std(r2s)), 4)
        self.mean_rmse = round(float(np.mean(rmses)), 2)
        self.std_rmse = round(float(np.std(rmses)), 2)
        self.mean_mae = round(float(np.mean(maes)), 2)
        self.std_mae = round(float(np.std(maes)), 2)
        self.mean_pearson_r = round(float(np.mean(rs)), 4)
        self.n_total = sum(f.n_test for f in self.fold_metrics)


def _compute_fold_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                          n_train: int, n_test: int) -> FoldMetrics:
    """Compute R-squared, RMSE, MAE, Pearson r for one fold."""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    r, _ = pearsonr(y_true, y_pred) if len(y_true) > 2 else (0.0, 1.0)
    return FoldMetrics(
        r_squared=round(r2, 4),
        rmse=round(rmse, 2),
        mae=round(mae, 2),
        pearson_r=round(float(r), 4),
        n_train=n_train,
        n_test=n_test,
    )


def _prepare_cv_data(df: pd.DataFrame):
    """Prepare feature matrix, target, and groups for CV."""
    feat = pd.DataFrame()
    feat["caffeine"] = df["caffeine_units"]
    feat["alcohol"] = df["alcohol_units"]
    feat["caf_x_alc"] = df["caffeine_units"] * df["alcohol_units"]
    feat["is_weekend"] = df["is_weekend"]
    feat["bedtime"] = df["bedtime_hours"]
    feat["sleep_duration"] = df["sleep_duration_hours"]
    feat["quality"] = df["sleep_quality_score"]
    feat["participant_id"] = df["participant_id"]

    feat.dropna(inplace=True)
    feat.reset_index(drop=True, inplace=True)
    return feat


# ---------------------------------------------------------------------------
# Model-specific CV predictors
# ---------------------------------------------------------------------------

def _cv_baseline_predict(X_train, y_train, X_test):
    """Hardcoded pathway baseline: predict using literature coefficients.

    Simple approximation of the pathway engine:
      quality = baseline - caffeine * 10.4 * (2/60) - alcohol * 3.04
                + caffeine * alcohol * 1.29
    """
    baseline = np.mean(y_train)
    caffeine = X_test[:, 0]
    alcohol = X_test[:, 1]
    caf_x_alc = X_test[:, 2]
    pred = (baseline
            - caffeine * 10.4 * (2.0 / 60.0)
            - alcohol * 3.04
            + caf_x_alc * 1.29)
    return pred


def _cv_calibrated_predict(X_train, y_train, X_test):
    """Calibrated pathway: learn coefficients on train, predict on test."""
    caffeine_tr = X_train[:, 0]
    alcohol_tr = X_train[:, 1]
    quality_tr = y_train

    no_sub = (caffeine_tr < 0.5) & (alcohol_tr < 0.5)
    baseline = np.mean(quality_tr[no_sub]) if np.sum(no_sub) > 5 else np.mean(quality_tr)

    def objective(params):
        mpc, qpd, inter = params
        pred = (baseline
                - alcohol_tr * qpd
                + caffeine_tr * alcohol_tr * inter
                - caffeine_tr * mpc * (2.0 / 60.0))
        return np.mean((quality_tr - pred) ** 2)

    result = minimize(objective, x0=[10.4, 3.04, 1.29],
                      bounds=[(0, 50), (0, 20), (0, 10)], method="L-BFGS-B")
    mpc, qpd, inter = result.x

    caffeine_te = X_test[:, 0]
    alcohol_te = X_test[:, 1]
    pred = (baseline
            - alcohol_te * qpd
            + caffeine_te * alcohol_te * inter
            - caffeine_te * mpc * (2.0 / 60.0))
    return pred


def _cv_ols_predict(X_train, y_train, X_test):
    """OLS regression: fit on train, predict on test."""
    X_tr = sm.add_constant(X_train[:, :4])  # caffeine, alcohol, caf_x_alc, is_weekend
    X_te = sm.add_constant(X_test[:, :4])
    model = sm.OLS(y_train, X_tr).fit()
    return model.predict(X_te)


def _cv_rf_predict(X_train, y_train, X_test):
    """Random Forest: fit on train, predict on test."""
    rf = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    return rf.predict(X_test)


# ---------------------------------------------------------------------------
# Main cross-validation
# ---------------------------------------------------------------------------

def cross_validate_all(df: pd.DataFrame, n_splits: int = 5) -> Dict[str, ModelCVResults]:
    """Run GroupKFold cross-validation for all model tiers.

    Returns a dict mapping model name to its CV results.
    """
    feat = _prepare_cv_data(df)
    X_cols = ["caffeine", "alcohol", "caf_x_alc", "is_weekend", "bedtime", "sleep_duration"]
    X = feat[X_cols].values
    y = feat["quality"].values
    groups = feat["participant_id"].values

    gkf = GroupKFold(n_splits=n_splits)

    models = {
        "Hardcoded Pathways (baseline)": _cv_baseline_predict,
        "A: Calibrated Pathways": _cv_calibrated_predict,
        "B: OLS Regression": _cv_ols_predict,
        "D: Random Forest": _cv_rf_predict,
    }

    results: Dict[str, ModelCVResults] = {}

    for name, predictor in models.items():
        cv_result = ModelCVResults(model_name=name)

        for fold_idx, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups)):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            try:
                y_pred = predictor(X_train, y_train, X_test)
                metrics = _compute_fold_metrics(y_test, y_pred, len(train_idx), len(test_idx))
                cv_result.fold_metrics.append(metrics)
            except Exception as e:
                log.warning("Fold %d failed for %s: %s", fold_idx, name, e)

        cv_result.compute_summary()
        results[name] = cv_result
        log.info(
            "CV %s: R^2=%.4f +/- %.4f, RMSE=%.2f, MAE=%.2f, r=%.4f (n=%d)",
            name, cv_result.mean_r_squared, cv_result.std_r_squared,
            cv_result.mean_rmse, cv_result.mean_mae,
            cv_result.mean_pearson_r, cv_result.n_total,
        )

    return results


def comparison_table(cv_results: Dict[str, ModelCVResults]) -> pd.DataFrame:
    """Build a comparison table from CV results."""
    rows = []
    for name, res in cv_results.items():
        rows.append({
            "Model": name,
            "CV R-squared": f"{res.mean_r_squared:.4f} +/- {res.std_r_squared:.4f}",
            "CV RMSE": f"{res.mean_rmse:.2f} +/- {res.std_rmse:.2f}",
            "CV MAE": f"{res.mean_mae:.2f} +/- {res.std_mae:.2f}",
            "Pearson r": f"{res.mean_pearson_r:.4f}",
            "N": res.n_total,
        })
    return pd.DataFrame(rows)
