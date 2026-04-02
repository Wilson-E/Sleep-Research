
import os
from dataclasses import dataclass

@dataclass
class Settings:
    data_dir: str = os.getenv("DATA_DIR", "./data")
    log_dir: str = os.getenv("LOG_DIR", "./data/logs")

settings = Settings()
