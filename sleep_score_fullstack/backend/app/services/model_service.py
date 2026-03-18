import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from dataclasses import dataclass

@dataclass
class TradersModels:
    duration_model: LinearRegression
    ssq_model: LinearRegression

@dataclass
class DidikogluModels:
    latency_model: LinearRegression

class ModelService:
    """Loads datasets and trains simple baseline models at startup.

    These are intentionally simple 'starter' models:
    - Traders (Song & Walker 2023): predict sleep duration and sleep quality from caffeine, alcohol, interaction, weekend.
    - Didikoglu et al. (PNAS 2023): predict sleep onset latency from caffeine, alcohol, workday.

    The Light and Chrononutrition papers are used as rule-based adjustments (in scoring.py).
    """

    def __init__(self, traders_csv_path: str, didikoglu_csv_path: str):
        self.traders_csv_path = traders_csv_path
        self.didikoglu_csv_path = didikoglu_csv_path

        self.traders: TradersModels | None = None
        self.didikoglu: DidikogluModels | None = None

        self._train_all()

    def _train_all(self):
        self.traders = self._train_traders(self.traders_csv_path)
        self.didikoglu = self._train_didikoglu(self.didikoglu_csv_path)

    @staticmethod
    def _train_traders(path: str) -> TradersModels:
        df = pd.read_csv(path)
        # Basic cleaning
        df = df.dropna(subset=["Duration", "SSQ", "Caffeine", "Alcohol", "Weekend"])
        # Features
        X = pd.DataFrame({
            "caffeine": df["Caffeine"].astype(float),
            "alcohol": df["Alcohol"].astype(float),
            "caf_x_alc": df["Caffeine"].astype(float) * df["Alcohol"].astype(float),
            "weekend": df["Weekend"].astype(int),
        })

        y_duration = df["Duration"].astype(float)
        y_ssq = df["SSQ"].astype(float)

        duration_model = LinearRegression().fit(X, y_duration)
        ssq_model = LinearRegression().fit(X, y_ssq)
        return TradersModels(duration_model=duration_model, ssq_model=ssq_model)

    @staticmethod
    def _train_didikoglu(path: str) -> DidikogluModels:
        df = pd.read_csv(path)
        # workdayYesterday is 'Work'/'Free'
        df = df.dropna(subset=["sleepOnsetLatencyYesterday", "caffeineYesterdayUnit", "alcoholYesterdayUnit", "workdayYesterday"])
        df["workday"] = (df["workdayYesterday"].astype(str).str.lower() == "work").astype(int)

        X = pd.DataFrame({
            "caffeine": df["caffeineYesterdayUnit"].astype(float),
            "alcohol": df["alcoholYesterdayUnit"].astype(float),
            "caf_x_alc": df["caffeineYesterdayUnit"].astype(float) * df["alcoholYesterdayUnit"].astype(float),
            "workday": df["workday"].astype(int),
        })
        y_latency = df["sleepOnsetLatencyYesterday"].astype(float)  # hours

        latency_model = LinearRegression().fit(X, y_latency)
        return DidikogluModels(latency_model=latency_model)
