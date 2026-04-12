"""
model_router.py
===============
API endpoints for model validation metrics and comparison.

These are additive endpoints; the existing /api/predict stays untouched.

Endpoints:
    GET /api/model/metrics     — validation metrics for each model tier
    GET /api/model/comparison  — full comparison table + model details
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/model", tags=["model-validation"])

# The trained_model_service instance is injected by main.py
_service = None


def set_service(service) -> None:
    """Called by main.py to inject the TrainedModelService instance."""
    global _service
    _service = service


@router.get("/metrics")
async def get_metrics():
    """Return cross-validation metrics for all model tiers."""
    if _service is None or not _service.is_ready:
        raise HTTPException(503, "Trained models not ready")
    return _service.get_metrics_dict()


@router.get("/comparison")
async def get_comparison():
    """Return full model comparison: CV table, coefficients, SEM results, RF importance."""
    if _service is None or not _service.is_ready:
        raise HTTPException(503, "Trained models not ready")
    return _service.get_comparison_dict()
