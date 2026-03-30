
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import PredictRequest, PredictResponse
from app.services.scoring import score_sleep

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sleep-score-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting pathway-based sleep simulation service...")
    log.info("Ready")
    yield

app = FastAPI(title="Sleep Score API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    score, components, breakdown, model_info = score_sleep(req)
    return PredictResponse(
        sleep_score=score,
        components=components,
        breakdown=breakdown,
        model_info=model_info,
    )
