import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import PredictRequest, PredictResponse
from app.services.model_service import ModelService
from app.services.scoring import score_sleep
from app.utils.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sleep-score-api")

models: ModelService | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global models
    log.info("Loading datasets + training starter models...")
    models = ModelService(settings.traders_csv, settings.didikoglu_csv)
    log.info("Ready")
    yield

app = FastAPI(title="Sleep Score API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

@app.get("/")
async def root():
    return {"status": "running", "service": "sleep-score"}

@app.get("/health")
async def health():
    return {
        "status": "healthy" if models else "starting",
        "traders_model": models is not None and models.traders is not None,
        "didikoglu_model": models is not None and models.didikoglu is not None,
    }

@app.post("/api/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    if not models:
        raise HTTPException(503, "Service not ready")

    score, components, breakdown, model_info = score_sleep(req, models)
    return PredictResponse(
        sleep_score=score,
        components=components,
        breakdown=breakdown,
        model_info=model_info,
    )
