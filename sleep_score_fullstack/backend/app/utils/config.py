
import os
from dataclasses import dataclass

@dataclass
class Settings:
    data_dir: str = os.getenv("DATA_DIR", "./data")

settings = Settings()
