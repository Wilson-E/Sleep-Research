
from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from app.services.linreg import LinearModel, fit_ols


@dataclass
class TradersModels:
    """Models trained on Song & Walker traders dataset (row-level)."""
    duration_minutes: LinearModel   # predict Duration (minutes)
    ssq: LinearModel                # predict SSQ (0-100)


class ModelService:
    """Loads datasets and trains small baseline models at startup.

    Key design choice:
    - No sklearn/numpy dependency (to avoid Python 3.13 build issues).
    - These models are *starter* regressions: useful for demo + slider interactivity,
      not meant to be clinical-grade prediction.

    Datasets expected in backend/data:
      - financial_traders_data.csv
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.traders: Optional[TradersModels] = None

    def load(self) -> None:
        self.traders = self._train_traders_models(self.data_dir / "financial_traders_data.csv")

    @staticmethod
    def _safe_float(x: str) -> Optional[float]:
        try:
            if x is None:
                return None
            x = str(x).strip()
            if x == "" or x.lower() in {"na", "nan", "none"}:
                return None
            return float(x)
        except Exception:
            return None

    def _train_traders_models(self, path: Path) -> TradersModels:
        # Expected columns: Weekend, Caffeine, Alcohol, Duration, SSQ
        X: List[List[float]] = []
        y_dur: List[float] = []
        y_ssq: List[float] = []

        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                weekend = self._safe_float(row.get("Weekend")) or 0.0
                caffeine = self._safe_float(row.get("Caffeine"))
                alcohol = self._safe_float(row.get("Alcohol"))
                dur = self._safe_float(row.get("Duration"))   # minutes in provided file
                ssq = self._safe_float(row.get("SSQ"))
                if caffeine is None or alcohol is None or dur is None or ssq is None:
                    continue

                caf_x_alc = caffeine * alcohol
                X.append([caffeine, alcohol, caf_x_alc, weekend])
                y_dur.append(dur)
                y_ssq.append(ssq)

        if len(X) < 10:
            raise RuntimeError(f"Not enough rows to train traders models from {path}")

        dur_model = fit_ols(X, y_dur)
        ssq_model = fit_ols(X, y_ssq)
        return TradersModels(duration_minutes=dur_model, ssq=ssq_model)
