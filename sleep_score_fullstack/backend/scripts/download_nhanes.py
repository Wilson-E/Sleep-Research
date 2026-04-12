"""
download_nhanes.py
==================
Downloads additional NHANES 2017-March 2020 pre-pandemic XPT files
needed for sleep + dietary analysis.

Already present in data/:
  - P_DR1IFF.xpt.txt  (Individual Foods, Day 1)
  - P_DR1TOT.xpt.txt  (Total Nutrient Intakes, Day 1)
  - P_DR2IFF.xpt.txt  (Individual Foods, Day 2)
  - P_DR2TOT.xpt.txt  (Total Nutrient Intakes, Day 2)

This script downloads:
  - P_SLQ.xpt   (Sleep Disorders Questionnaire)
  - P_DEMO.xpt  (Demographics)
  - P_BMX.xpt   (Body Measures)

All files are linked via SEQN (participant sequence number).

Usage:
    python scripts/download_nhanes.py
"""

import os
import urllib.request
from pathlib import Path

BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles"

FILES = {
    "P_SLQ.xpt": f"{BASE_URL}/P_SLQ.xpt",
    "P_DEMO.xpt": f"{BASE_URL}/P_DEMO.xpt",
    "P_BMX.xpt": f"{BASE_URL}/P_BMX.xpt",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def download_file(url: str, dest: Path) -> None:
    if dest.exists():
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  Already exists: {dest.name} ({size_mb:.1f} MB), skipping.")
        return

    print(f"  Downloading {dest.name} from {url} ...")
    urllib.request.urlretrieve(url, dest)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  Saved: {dest.name} ({size_mb:.1f} MB)")


def main() -> None:
    print(f"Data directory: {DATA_DIR}")
    if not DATA_DIR.exists():
        print(f"Creating {DATA_DIR}")
        DATA_DIR.mkdir(parents=True)

    for filename, url in FILES.items():
        download_file(url, DATA_DIR / filename)

    print("\nVerifying all required files are present...")
    required = list(FILES.keys()) + [
        "P_DR1TOT.xpt.txt",
        "P_DR2TOT.xpt.txt",
        "financial_traders_data.csv",
        "Didikoglu_et_al_2023_PNAS_sleep.csv",
    ]
    for f in required:
        path = DATA_DIR / f
        if path.exists():
            print(f"  OK: {f}")
        else:
            print(f"  MISSING: {f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
