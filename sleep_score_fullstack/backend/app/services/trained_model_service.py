"""
trained_model_service.py
========================
Orchestrates loading data, training all model tiers, and running
cross-validation at startup. Provides access to trained models
and validation metrics for the API layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from app.services.data_harmonizer import load_harmonized
from app.services.model_trainer import AllModels, train_all_models
from app.services.model_validator import (
    ModelCVResults,
    comparison_table,
    cross_validate_all,
)

log = logging.getLogger(__name__)


@dataclass
class TrainedModelService:
    """Holds all trained models, validation metrics, and the harmonized dataset."""
    models: Optional[AllModels] = None
    cv_results: Dict[str, ModelCVResults] = field(default_factory=dict)
    comparison_df: Optional[pd.DataFrame] = None
    harmonized_data: Optional[pd.DataFrame] = None
    is_ready: bool = False

    def load(self, data_dir: Path) -> None:
        """Load data, train models, and run cross-validation."""
        log.info("Loading harmonized dataset from %s...", data_dir)
        self.harmonized_data = load_harmonized(data_dir)
        log.info("Harmonized dataset: %d rows", len(self.harmonized_data))

        log.info("Training all model tiers...")
        self.models = train_all_models(self.harmonized_data)

        log.info("Running 5-fold cross-validation...")
        self.cv_results = cross_validate_all(self.harmonized_data, n_splits=5)
        self.comparison_df = comparison_table(self.cv_results)

        self.is_ready = True
        log.info("TrainedModelService ready.")

    def get_metrics_dict(self) -> Dict:
        """Return validation metrics as a serializable dict."""
        if not self.is_ready:
            return {"error": "Models not loaded"}

        metrics = {}
        for name, res in self.cv_results.items():
            metrics[name] = {
                "mean_r_squared": res.mean_r_squared,
                "std_r_squared": res.std_r_squared,
                "mean_rmse": res.mean_rmse,
                "std_rmse": res.std_rmse,
                "mean_mae": res.mean_mae,
                "std_mae": res.std_mae,
                "mean_pearson_r": res.mean_pearson_r,
                "n_observations": res.n_total,
                "n_folds": len(res.fold_metrics),
            }
        return metrics

    def get_comparison_dict(self) -> Dict:
        """Return comparison table as a serializable dict."""
        if not self.is_ready or self.comparison_df is None:
            return {"error": "Models not loaded"}

        return {
            "models": self.comparison_df.to_dict(orient="records"),
            "dataset": {
                "total_rows": self.models.dataset_size if self.models else 0,
                "sources": self.models.dataset_sources if self.models else {},
            },
            "calibrated_coefficients": {
                "minutes_lost_per_cup": {
                    "learned": self.models.calibrated.minutes_lost_per_cup,
                    "literature": 10.4,
                },
                "quality_pen_per_drink": {
                    "learned": self.models.calibrated.quality_pen_per_drink,
                    "literature": 3.04,
                },
                "interaction_coeff": {
                    "learned": self.models.calibrated.interaction_coeff,
                    "literature": 1.29,
                },
            } if self.models else {},
            "sem_results": {
                "converged": self.models.sem.converged,
                "direct_effects": self.models.sem.direct_effects,
                "indirect_effects": self.models.sem.indirect_effects,
                "fit_indices": self.models.sem.fit_indices,
            } if self.models else {},
            "ols_results": {
                "quality_r_squared": self.models.ols.quality_r_squared,
                "quality_adj_r_squared": self.models.ols.quality_adj_r_squared,
                "quality_coefficients": self.models.ols.quality_coefficients,
                "quality_vif": self.models.ols.quality_vif,
                "duration_r_squared": self.models.ols.duration_r_squared,
                "duration_coefficients": self.models.ols.duration_coefficients,
            } if self.models else {},
            "rf_results": {
                "oob_r_squared": self.models.rf.oob_score,
                "feature_importances": self.models.rf.feature_importances,
            } if self.models else {},
        }
