"""
bayesian_updater.py
===================
Conjugate Normal-Normal Bayesian updating of per-user sleep coefficient profiles.

Each coefficient starts at its published population-level value (prior) and
adapts as the user logs real sleep outcomes. After ~5-10 nights of data the
profile begins to reflect individual variation in caffeine metabolism, alcohol
sensitivity, light response, and meal-timing sensitivity.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional

from app.services.sleep_log import SleepLogEntry
from app.utils.math_utils import clamp


# ---------------------------------------------------------------------------
# Coefficient prior
# ---------------------------------------------------------------------------

@dataclass
class CoefficientPrior:
    """A single coefficient modeled as a Normal distribution."""

    name: str
    mu: float           # current posterior mean
    sigma: float        # current posterior std dev
    base_mu: float      # original published value (immutable)
    base_sigma: float   # original uncertainty (immutable)
    n_updates: int = 0  # how many observations have updated this coefficient

    @property
    def confidence(self) -> float:
        """0-1 scale: how much the coefficient has been personalized away from prior."""
        if self.n_updates == 0:
            return 0.0
        return min(1.0, 1.0 - (self.sigma / self.base_sigma))

    def update(self, observed_value: float, observation_sigma: float) -> None:
        """Conjugate Normal-Normal Bayesian update."""
        prior_precision = 1.0 / (self.sigma ** 2)
        likelihood_precision = 1.0 / (observation_sigma ** 2)

        posterior_precision = prior_precision + likelihood_precision
        posterior_mu = (
            self.mu * prior_precision + observed_value * likelihood_precision
        ) / posterior_precision
        posterior_sigma = math.sqrt(1.0 / posterior_precision)

        self.mu = posterior_mu
        self.sigma = posterior_sigma
        self.n_updates += 1

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "current_value": round(self.mu, 4),
            "uncertainty": round(self.sigma, 4),
            "base_value": self.base_mu,
            "confidence": round(self.confidence, 3),
            "n_updates": self.n_updates,
        }


# ---------------------------------------------------------------------------
# Default priors from published literature
# ---------------------------------------------------------------------------

# Population-level priors. Each mu is drawn from the published study named in
# the comment; sigma is set to roughly one-third of mu so that confidence
# (1 - sigma/base_sigma) starts near zero and approaches 1.0 as a user logs
# consistent nights.
_DEFAULT_PRIORS: Dict[str, CoefficientPrior] = {
    # Song and Walker (2023): 10.4 min of sleep lost per caffeinated cup.
    "caffeine_duration_min_per_cup": CoefficientPrior(
        name="caffeine_duration_min_per_cup",
        mu=10.4, sigma=4.0, base_mu=10.4, base_sigma=4.0,
    ),
    # Standard pharmacokinetic half-life for caffeine in healthy adults.
    "caffeine_half_life_hours": CoefficientPrior(
        name="caffeine_half_life_hours",
        mu=6.0, sigma=1.5, base_mu=6.0, base_sigma=1.5,
    ),
    # Song and Walker (2023): 3.04 quality points lost per alcoholic drink.
    "alcohol_quality_per_drink": CoefficientPrior(
        name="alcohol_quality_per_drink",
        mu=3.04, sigma=1.5, base_mu=3.04, base_sigma=1.5,
    ),
    # Didikoglu et al. (2023): ~30 min of added sleep-onset latency per
    # log10(lux) of evening light above the ~10 lux reference.
    "light_sol_min_per_log_lux": CoefficientPrior(
        name="light_sol_min_per_log_lux",
        mu=30.0, sigma=10.0, base_mu=30.0, base_sigma=10.0,
    ),
    # Unit-mean sensitivity multipliers; personal deviations around 1.0 are
    # learned from observed residuals over ~5 to 10 logged nights.
    "meal_timing_sensitivity": CoefficientPrior(
        name="meal_timing_sensitivity",
        mu=1.0, sigma=0.3, base_mu=1.0, base_sigma=0.3,
    ),
    "evening_diet_sensitivity": CoefficientPrior(
        name="evening_diet_sensitivity",
        mu=1.0, sigma=0.3, base_mu=1.0, base_sigma=0.3,
    ),
}


# ---------------------------------------------------------------------------
# Personalizer
# ---------------------------------------------------------------------------

class BayesianPersonalizer:
    """
    Manages personalized coefficient profiles for users.
    Profiles are stored as JSON files alongside sleep logs.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def get_profile(self, user_id: str) -> Dict[str, CoefficientPrior]:
        path = self._user_path(user_id)
        if not path.exists():
            return self._fresh_priors()
        with path.open() as f:
            data = json.load(f)
        priors: Dict[str, CoefficientPrior] = {}
        for name, vals in data.get("coefficients", {}).items():
            priors[name] = CoefficientPrior(**vals)
        # Add any new coefficients that may not exist in older profiles
        fresh = self._fresh_priors()
        for key in fresh:
            if key not in priors:
                priors[key] = fresh[key]
        return priors

    def update_from_log(
        self,
        user_id: str,
        log_entry: SleepLogEntry,
    ) -> Dict[str, CoefficientPrior]:
        """
        Given a log entry with both predicted and observed scores, compute
        implied coefficient adjustments and perform Bayesian updates.

        Residual = predicted - observed.
        Positive residual: engine was too optimistic → user sleeps worse than
        predicted → penalty coefficients should be higher.
        Negative residual: engine was too pessimistic → coefficients lower.

        The residual is distributed equally across active pathways; each
        pathway's implied coefficient is updated independently.
        """
        if log_entry.observed_score is None:
            return self.get_profile(user_id)

        profile = self.get_profile(user_id)

        residual = log_entry.predicted_score - log_entry.observed_score

        # Determine which pathways had meaningful input this night
        caffeine_active = any(d.get("mg", 0) > 0 for d in log_entry.caffeine_doses)
        alcohol_active = log_entry.alcohol_drinks > 0
        light_active = log_entry.evening_light_lux > 15
        meal_active = (
            log_entry.hours_wake_to_first_eat > 1.5
            or log_entry.hours_last_eat_to_bed < 2.5
        )

        active_pathways = sum([caffeine_active, alcohol_active, light_active, meal_active])
        if active_pathways == 0:
            self._save(user_id, profile)
            return profile

        per_pathway_residual = residual / active_pathways

        # Observation noise for a single night's residual. Sigma is large on
        # purpose: one surprising night should nudge the prior only slightly,
        # so it takes roughly 5 to 10 consistent nights to shift a coefficient.
        obs_sigma = 15.0

        # Each per-pathway update converts a score-point residual into an
        # implied coefficient shift, then scales that shift by a damping factor
        # (0.5, 0.3, 0.2, 0.01). The damping factors reflect how much of a
        # night's residual is plausibly attributable to that pathway's
        # coefficient (caffeine is most directly dose-linked, meal timing is
        # mostly captured by the sensitivity multiplier instead of a slope).

        if caffeine_active:
            total_mg = sum(d.get("mg", 0) for d in log_entry.caffeine_doses)
            total_cups = total_mg / 95.0  # 95 mg per standard cup-equivalent
            if total_cups > 0.25:
                current = profile["caffeine_duration_min_per_cup"].mu
                implied = current + (per_pathway_residual / total_cups) * 0.5
                implied = clamp(implied, 0.0, 40.0)
                profile["caffeine_duration_min_per_cup"].update(implied, obs_sigma)

        if alcohol_active and log_entry.alcohol_drinks > 0.25:
            current = profile["alcohol_quality_per_drink"].mu
            implied = current + (per_pathway_residual / log_entry.alcohol_drinks) * 0.3
            implied = clamp(implied, 0.0, 15.0)
            profile["alcohol_quality_per_drink"].update(implied, obs_sigma)

        if light_active:
            current = profile["light_sol_min_per_log_lux"].mu
            implied = current + per_pathway_residual * 0.2
            implied = clamp(implied, 5.0, 90.0)
            profile["light_sol_min_per_log_lux"].update(implied, obs_sigma)

        if meal_active:
            current = profile["meal_timing_sensitivity"].mu
            implied = current + per_pathway_residual * 0.01
            implied = clamp(implied, 0.3, 3.0)
            # Use half the usual obs_sigma for the sensitivity multiplier so
            # that repeated meal-timing deviations update it faster than the
            # pharmacology-backed coefficients above.
            profile["meal_timing_sensitivity"].update(implied, obs_sigma * 0.5)

        self._save(user_id, profile)
        return profile

    def _fresh_priors(self) -> Dict[str, CoefficientPrior]:
        return {k: copy.deepcopy(v) for k, v in _DEFAULT_PRIORS.items()}

    def _user_path(self, user_id: str) -> Path:
        safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
        return self.storage_dir / f"{safe_id}_profile.json"

    def _save(self, user_id: str, profile: Dict[str, CoefficientPrior]) -> None:
        path = self._user_path(user_id)
        data = {"coefficients": {k: asdict(v) for k, v in profile.items()}}
        with path.open("w") as f:
            json.dump(data, f, indent=2)
