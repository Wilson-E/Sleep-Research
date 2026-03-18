import os
from dataclasses import dataclass

@dataclass
class Settings:
    traders_csv: str = os.getenv("TRADERS_CSV", "./data/financial_traders_data.csv")
    didikoglu_csv: str = os.getenv("DIDIKOGLOU_CSV", "./data/Didikoglu_et_al_2023_PNAS_sleep.csv")

settings = Settings()
