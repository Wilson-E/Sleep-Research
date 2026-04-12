
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import (
    ObservedOutcomeRequest,
    PredictRequest,
    PredictResponse,
    SleepLogRequest,
    SleepLogResponse,
    SleepLogStatsResponse,
    UserProfileResponse,
)
from app.services.bayesian_updater import BayesianPersonalizer
from app.services.scoring import score_sleep
from app.services.sleep_log import SleepLogEntry, SleepLogStore
from app.services.trained_model_service import TrainedModelService
from app.routers import model_router
from app.utils.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sleep-score-api")

sleep_log_store: Optional[SleepLogStore] = None
bayesian_personalizer: Optional[BayesianPersonalizer] = None
trained_models: Optional[TrainedModelService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sleep_log_store, bayesian_personalizer, trained_models
    log_path = Path(settings.log_dir)
    sleep_log_store = SleepLogStore(log_path)
    bayesian_personalizer = BayesianPersonalizer(log_path)
    log.info("Starting pathway-based sleep simulation service...")
    log.info("Sleep log store initialized at %s", log_path)

    # Train model tiers and run cross-validation
    trained_models = TrainedModelService()
    try:
        trained_models.load(Path(settings.data_dir))
        model_router.set_service(trained_models)
        log.info("Trained model service ready with %d rows", trained_models.models.dataset_size)
    except Exception as e:
        log.warning("Trained model service failed to load (non-fatal): %s", e)

    log.info("Ready")
    yield


app = FastAPI(title="Sleep Score API", version="0.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(model_router.router)


@app.get("/")
async def root():
    return {"status": "running", "service": "sleep-score"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "engine": "pathway-simulation",
    }


@app.post("/api/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    profile = None
    if req.user_id and bayesian_personalizer:
        profile = bayesian_personalizer.get_profile(req.user_id)
    score, components, breakdown, model_info = score_sleep(req, profile=profile)
    return PredictResponse(
        sleep_score=score,
        components=components,
        breakdown=breakdown,
        model_info=model_info,
    )


@app.post("/api/log")
async def log_night(req: SleepLogRequest):
    """Log tonight's inputs and store the predicted score."""
    if sleep_log_store is None or bayesian_personalizer is None:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    profile = bayesian_personalizer.get_profile(req.user_id)
    predict_req = req.predict_request
    score, components, _, _ = score_sleep(predict_req, profile=profile)

    date_str = req.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    timestamp = datetime.now(timezone.utc).isoformat()

    # Derive bedtime for storage
    wake_time = 7.5 if predict_req.weekend else 6.5
    first_meal = wake_time + predict_req.hours_wake_to_first_eat
    last_meal = first_meal + predict_req.eating_window_hours
    derived_bedtime = last_meal + predict_req.hours_last_eat_to_bed
    bedtime = predict_req.bedtime_hours if predict_req.bedtime_hours is not None else derived_bedtime

    # Serialize caffeine doses
    if predict_req.caffeine_doses:
        caffeine_doses = [
            {"time": d.time_hours_after_midnight, "mg": d.dose_mg}
            for d in predict_req.caffeine_doses
        ]
    else:
        caffeine_doses = []

    entry = SleepLogEntry(
        date=date_str,
        timestamp=timestamp,
        caffeine_doses=caffeine_doses,
        alcohol_drinks=predict_req.alcohol_drinks,
        alcohol_last_drink_time=predict_req.alcohol_last_drink_time,
        morning_light_lux=predict_req.morning_light_lux,
        evening_light_lux=predict_req.evening_light_lux,
        night_light_minutes=predict_req.night_light_minutes,
        hours_wake_to_first_eat=predict_req.hours_wake_to_first_eat,
        hours_last_eat_to_bed=predict_req.hours_last_eat_to_bed,
        eating_window_hours=predict_req.eating_window_hours,
        bedtime_hours=bedtime,
        screen_time_before_bed_minutes=predict_req.screen_time_before_bed_minutes,
        weekend=predict_req.weekend,
        predicted_score=score,
        predicted_components=components,
    )

    sleep_log_store.add_entry(req.user_id, entry)
    log.info("Logged night for user=%s date=%s predicted_score=%.1f", req.user_id, date_str, score)

    return {
        "status": "logged",
        "date": date_str,
        "predicted_score": score,
        "predicted_components": components,
    }


@app.put("/api/log/{date}/observed")
async def log_observed(date: str, req: ObservedOutcomeRequest):
    """Update a log entry with morning-after observed outcomes, then run Bayesian update."""
    if sleep_log_store is None or bayesian_personalizer is None:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    observed = {
        "observed_sleep_duration_hours": req.observed_sleep_duration_hours,
        "observed_sleep_quality_subjective": req.observed_sleep_quality_subjective,
        "observed_sleep_onset_latency_minutes": req.observed_sleep_onset_latency_minutes,
        "observed_awakenings": req.observed_awakenings,
        "observed_morning_alertness": req.observed_morning_alertness,
    }

    updated_entry = sleep_log_store.update_entry_observed(req.user_id, date, observed)
    if updated_entry is None:
        raise HTTPException(status_code=404, detail=f"No log entry found for date={date} user={req.user_id}")

    updated_profile = bayesian_personalizer.update_from_log(req.user_id, updated_entry)

    log.info(
        "Observed outcomes logged for user=%s date=%s observed_score=%s",
        req.user_id, date, updated_entry.observed_score,
    )

    return {
        "status": "updated",
        "date": date,
        "observed_score": updated_entry.observed_score,
        "predicted_score": updated_entry.predicted_score,
        "residual": (
            round(updated_entry.predicted_score - updated_entry.observed_score, 1)
            if updated_entry.observed_score is not None
            else None
        ),
        "updated_coefficients": {k: v.to_dict() for k, v in updated_profile.items()},
    }


@app.get("/api/log", response_model=SleepLogResponse)
async def get_log(user_id: str = "default"):
    """Get all log entries for a user."""
    if sleep_log_store is None:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    from dataclasses import asdict
    entries = sleep_log_store.get_entries(user_id)
    return SleepLogResponse(
        entries=[asdict(e) for e in entries],
        total_entries=len(entries),
    )


@app.get("/api/log/stats", response_model=SleepLogStatsResponse)
async def get_log_stats(user_id: str = "default"):
    """Get summary statistics for a user's sleep log."""
    if sleep_log_store is None:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    entries = sleep_log_store.get_entries(user_id)
    with_outcomes = [e for e in entries if e.observed_score is not None]

    avg_predicted = (
        round(sum(e.predicted_score for e in entries) / len(entries), 1)
        if entries else None
    )
    avg_observed = (
        round(sum(e.observed_score for e in with_outcomes) / len(with_outcomes), 1)
        if with_outcomes else None
    )
    avg_residual = (
        round(
            sum(e.predicted_score - e.observed_score for e in with_outcomes) / len(with_outcomes),
            1,
        )
        if with_outcomes else None
    )

    return SleepLogStatsResponse(
        user_id=user_id,
        total_entries=len(entries),
        entries_with_outcomes=len(with_outcomes),
        avg_predicted_score=avg_predicted,
        avg_observed_score=avg_observed,
        avg_residual=avg_residual,
    )


@app.get("/api/profile", response_model=UserProfileResponse)
async def get_profile(user_id: str = "default"):
    """Get current personalized coefficient profile for a user."""
    if sleep_log_store is None or bayesian_personalizer is None:
        raise HTTPException(status_code=503, detail="Log store not initialized")

    profile = bayesian_personalizer.get_profile(user_id)
    entries = sleep_log_store.get_entries(user_id)
    with_outcomes = [e for e in entries if e.observed_score is not None]

    return UserProfileResponse(
        user_id=user_id,
        total_logs=len(entries),
        logs_with_outcomes=len(with_outcomes),
        personalized_coefficients={k: round(v.mu, 4) for k, v in profile.items()},
        coefficient_confidence={k: round(v.confidence, 3) for k, v in profile.items()},
        base_coefficients={k: v.base_mu for k, v in profile.items()},
    )
