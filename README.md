# Vitality Core: A Transparent Pathway-Based Sleep Quality Simulator

**Penn State DS340W, Group 39**

Vitality Core predicts a 0 to 100 nightly sleep score from everyday lifestyle inputs (caffeine, alcohol, meal timing, evening light exposure, and evening diet). Instead of training a single opaque model, the engine applies five published regression coefficients as independent "pathways," then combines them into a composite score. The same core is exposed through three interfaces: a command-line simulator (the primary research artifact), a FastAPI REST service, and an optional React web application. A companion training pipeline validates the pathway engine against three merged datasets (roughly 6,166 observations) using four model tiers, producing the cross-validation numbers reported in the research paper.

This README walks a new reviewer from a fresh `git clone` to the results quoted in the paper.

---

## Repository Layout

```
Sleep-Research/
  CLAUDE.md                      Project instructions for AI-assisted development
  README.md                      You are here
  figures/                       Generated on demand by scripts/generate_figures.py
  sleep_score_fullstack/
    backend/                     Pathway engine, training pipeline, FastAPI service
      app/                       Application code (routers, services, utils, schemas)
      data/
        datasets.zip             All datasets (CSVs + NHANES XPTs), unzip before running
        logs/                    Local-only sleep history; one JSON per user (gitignored)
      scripts/
        predict_cli.py           Interactive CLI simulator (main research tool)
        generate_figures.py      Regenerates Figures 1 to 6 and Table I data
        scenarios.py             Runs the 8 canonical scenarios used in the paper
        log_cli.py               Log a completed night and trigger Bayesian updating
        download_nhanes.py       Alternative NHANES downloader (not needed if using zip)
        caffeine_sensitivity_calibration.py  Sensitivity multiplier calibration
      requirements.txt           Python dependencies
    frontend/                    Optional React + Vite UI
      src/                       React pages and API client
      package.json               Frontend dependencies
```

---

## Prerequisites

| Tool | Version | Required For |
|------|---------|--------------|
| Python | 3.11, 3.12, or 3.13 (3.14 is **not** supported) | Backend, CLI simulator, figures |
| pip | Any recent version | Installing Python dependencies |
| git | Any recent version | Cloning the repository |
| Node.js | 18+ (optional) | Running the frontend locally |

Apple Silicon users: if `pip install` fails on `semopy` or `numpy`, upgrade pip first (`pip install --upgrade pip`) and retry.

---

## Quick Start (Reproduce the Paper Results)

Five steps take a fresh machine from clone to reproduced paper results. No server required.

### 1. Clone and enter the backend

```bash
git clone https://github.com/Wilson-E/Sleep-Research.git
cd Sleep-Research/sleep_score_fullstack/backend
```

Every command below assumes this working directory.

### 2. Unzip the datasets

All data files are stored in a single zip for size efficiency. Unzip them into the `data/` folder:

```bash
cd data
unzip datasets.zip
cd ..
```

This extracts seven files into `data/`:
- `financial_traders_data.csv` (Song and Walker 2023, 552 rows)
- `Didikoglu_et_al_2023_PNAS_sleep.csv` (Didikoglu et al. 2023, 478 rows)
- `P_SLQ.xpt`, `P_DEMO.xpt`, `P_BMX.xpt` (NHANES sleep, demographics, body measures)
- `P_DR1TOT.xpt.txt`, `P_DR2TOT.xpt.txt` (NHANES dietary recall totals)

### 3. Create a virtual environment and install dependencies

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the CLI simulator (the main research artifact)

```bash
python scripts/predict_cli.py
```

The CLI prompts for every behavioral input the web UI accepts (caffeine, alcohol, bedtime, meal timing, light exposure, screen time, optional HRV). Press Enter to accept the shown default for any field. The output is a composite sleep score, a bar for each of the four score components (Duration, Quality, Timing, Alertness), and the per-pathway breakdown that explains every point gained or lost. This is the transparency contribution called out in Section V of the paper.

Scripted alternatives:

```bash
python scripts/predict_cli.py --defaults            # use default payload, no prompts
python scripts/predict_cli.py --input profile.json  # read PredictRequest fields from JSON
```

### 5. Regenerate all six paper figures and Table I data

```bash
python scripts/generate_figures.py
```

This builds the harmonized 6,166-row validation dataset, trains the four model tiers, runs 5-fold GroupKFold cross-validation, and writes six PNG files into a `figures/` directory at the repo root:

| Output File | Paper Artifact |
|-------------|----------------|
| `fig1_sem_path_diagram.png` | Figure 1: Model C SEM with direct and indirect effects |
| `fig2_cv_comparison.png` | Figure 2: R-squared and RMSE bar chart across model tiers |
| `fig3_rf_feature_importance.png` | Figure 3: Random Forest feature importance |
| `fig4_observed_vs_predicted.png` | Figure 4: Observed vs predicted scatter (4 panels) |
| `fig5_bayesian_convergence.png` | Figure 5: Bayesian coefficient convergence (20 nights) |
| `fig6_scenarios.png` | Figure 6: Eight-scenario bar chart |

Table I data (CV metrics across model tiers) is printed to the terminal during figure generation.

To also print the scenario table and write a CSV:

```bash
python scripts/scenarios.py
```

---

## Reproducing Specific Paper Results

| Paper Artifact | Command |
|----------------|---------|
| Figures 1 through 6 and Table I | `python scripts/generate_figures.py` |
| Scenario table and mediation delta (Section IV.H) | `python scripts/scenarios.py` |
| End-to-end pathway prediction for any behavioral profile | `python scripts/predict_cli.py` |

If any output differs from the paper, verify that step 2 (unzip) completed successfully. Check that all seven data files exist in `backend/data/` by running `ls data/*.csv data/*.xpt data/*.xpt.txt`. Missing files cause the training pipeline to fall back to a smaller dataset, which yields different numbers.

---

## Optional: Run the FastAPI Server and REST API

Start the backend:

```bash
uvicorn app.main:app --port 8000
```

On startup, `TrainedModelService.load()` trains all four model tiers and runs cross-validation. Expect "Trained model service ready" in the log after one to two seconds. Once running:

```bash
curl http://localhost:8000/api/model/metrics | python -m json.tool
curl http://localhost:8000/api/model/comparison | python -m json.tool
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"caffeine_cups": 2, "alcohol_drinks": 1, "hours_last_eat_to_bed": 3, "evening_light_lux": 50}'
```

---

## Optional: Run the Frontend Locally

The React app is a demo UI. It does not affect any reported number.

**Requires [Node.js 18+](https://nodejs.org/).** If `npm` is not found, download and run the macOS `.pkg` installer from [nodejs.org/en/download](https://nodejs.org/en/download). It includes npm automatically.

```bash
cd ../../frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to `http://localhost:8000`, so the FastAPI server above must be running. The Simulator page calls `POST /api/predict`; the History page supports sleep logging and Bayesian personalization.

---

## Troubleshooting

1. **CLI simulator fails on Pydantic validation.** Your input violated a field range (e.g., caffeine_cups above 20). Re-run and accept the default for the offending field.
2. **`generate_figures.py` errors on "Trained model service failed to load".** A data file is missing. Re-run `unzip datasets.zip` in the `data/` directory and retry.
3. **Port 8000 is already in use.** Pick another port: `uvicorn app.main:app --port 8001`. Update the proxy target in `frontend/vite.config.js` accordingly.
4. **`pip install` fails on `semopy` or `numpy` (Apple Silicon).** Upgrade pip first, then retry.

---

## Primary Sources

The pathway coefficients are drawn from peer-reviewed research.

1. Song, C., and Walker, M. P. (2023). Sleep, alcohol, and caffeine in financial traders. *PLOS ONE*.
2. Kim, S., et al. (2024). Chrononutrition patterns and multidimensional sleep health (NHANES 2017 to 2020). *Nutrients*.
3. Didikoglu, A., et al. (2023). Light exposure and sleep timing in UK adults. *PNAS*.
4. Soares, L. de L., et al. (2025). Evening latency and sleep-disturbing diet on sleep quality. *J. Human Nutrition and Dietetics*.

NHANES 2017 to March 2020 (pre-pandemic) data are used for coefficient calibration and cross-validation. Source: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/.

---

## Contact

Penn State DS340W Group 39. Repository: https://github.com/Wilson-E/Sleep-Research.
