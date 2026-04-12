"""
sleep_simulation_engine.py
==========================
A pathway-based simulation engine for sleep scoring.
Each pathway uses published coefficients from specific studies rather than
training a single model on merged data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _log10_safe(x: float) -> float:
    return math.log10(max(1e-9, x))


# ---------------------------------------------------------------------------
# 1. CaffeinePathway
# ---------------------------------------------------------------------------

@dataclass
class CaffeineDose:
    """A single caffeinated drink consumed during the day."""

    time_hours_after_midnight: float
    dose_mg: float


@dataclass
class CaffeinePathway:
    """
    Models caffeine pharmacokinetic decay and downstream sleep penalties.
    """

    doses: List[CaffeineDose] = field(default_factory=list)
    bedtime_hours: float = 23.0
    half_life_hours: float = 6.0
    cup_equiv_mg: float = 95.0
    sensitivity_multiplier: float = 1.0

    # Calibrated from NHANES (n=5,116); literature value was 10.4 (Song & Walker 2023)
    _minutes_lost_per_cup: float = 9.07
    _quality_pen_per_cup: float = 2.0

    def _residual_mg(self) -> float:
        total = 0.0
        for dose in self.doses:
            hours_until_bed = self.bedtime_hours - dose.time_hours_after_midnight
            if hours_until_bed < 0:
                hours_until_bed = 0.0
            fraction_remaining = math.exp(-0.693 * hours_until_bed / self.half_life_hours)
            total += dose.dose_mg * fraction_remaining
        return total

    def compute(self) -> Dict[str, float]:
        residual_mg = self._residual_mg()
        residual_cups = residual_mg / self.cup_equiv_mg
        effective_residual_cups = residual_cups * self.sensitivity_multiplier

        duration_penalty_min = _clamp(effective_residual_cups * self._minutes_lost_per_cup, 0.0, 120.0)
        quality_penalty = _clamp(effective_residual_cups * self._quality_pen_per_cup, 0.0, 20.0)

        return {
            "residual_mg": round(residual_mg, 1),
            "residual_cups": round(residual_cups, 2),
            "effective_residual_cups": round(effective_residual_cups, 2),
            "sensitivity_multiplier": round(self.sensitivity_multiplier, 2),
            "duration_penalty_min": round(duration_penalty_min, 1),
            "quality_penalty": round(quality_penalty, 1),
        }


# ---------------------------------------------------------------------------
# 2. AlcoholPathway
# ---------------------------------------------------------------------------

@dataclass
class AlcoholPathway:
    """Models alcohol quality effects and caffeine interaction."""

    drinks: float = 0.0
    caffeine_cups: float = 0.0

    _quality_pen_per_drink: float = 3.04
    _interaction_coeff: float = 1.29

    def compute(self) -> Dict[str, float]:
        raw_pen = self.drinks * self._quality_pen_per_drink
        interaction_offset = self.drinks * self.caffeine_cups * self._interaction_coeff
        net_pen = _clamp(raw_pen - interaction_offset, 0.0, 40.0)

        return {
            "raw_quality_penalty": round(raw_pen, 2),
            "interaction_offset": round(interaction_offset, 2),
            "net_quality_penalty": round(net_pen, 2),
        }


# ---------------------------------------------------------------------------
# 3. MealTimingPathway
# ---------------------------------------------------------------------------

@dataclass
class MealTimingPathway:
    """Models chrononutrition timing effects with OR-based scaling."""

    wake_time_hours: float = 6.5
    first_meal_hours: float = 7.5
    last_meal_hours: float = 19.0
    bedtime_hours: float = 23.0
    sensitivity_multiplier: float = 1.0

    _or_wake_to_first_timing: float = 1.19
    _or_wake_to_first_duration: float = 1.21
    _or_last_to_bed_duration: float = 1.09
    _or_window_timing_protective: float = 0.90

    _max_timing_pen: float = 15.0
    _max_duration_pen: float = 15.0

    def _hours_wake_to_first(self) -> float:
        return max(0.0, self.first_meal_hours - self.wake_time_hours)

    def _hours_last_to_bed(self) -> float:
        return max(0.0, self.bedtime_hours - self.last_meal_hours)

    def _eating_window(self) -> float:
        return max(0.0, self.last_meal_hours - self.first_meal_hours)

    def _or_to_penalty(
        self, or_val: float, hours: float, max_pen: float, reference_hours: float = 3.0
    ) -> float:
        if hours <= 0:
            return 0.0
        numerator = or_val**hours - 1.0
        denominator = or_val**reference_hours - 1.0
        if denominator <= 0:
            return 0.0
        return _clamp(max_pen * numerator / denominator, 0.0, max_pen)

    def compute(self) -> Dict[str, float]:
        h_w2f = self._hours_wake_to_first()
        h_l2b = self._hours_last_to_bed()
        ew = self._eating_window()

        timing_pen = self._or_to_penalty(
            self._or_wake_to_first_timing, h_w2f, self._max_timing_pen
        ) * self.sensitivity_multiplier

        dur_pen_w2f = self._or_to_penalty(
            self._or_wake_to_first_duration, h_w2f, self._max_duration_pen * 0.6
        ) * self.sensitivity_multiplier
        dur_pen_l2b = self._or_to_penalty(
            self._or_last_to_bed_duration,
            max(0.0, 3.0 - h_l2b),
            self._max_duration_pen * 0.4,
        ) * self.sensitivity_multiplier
        duration_pen = dur_pen_w2f + dur_pen_l2b

        window_bonus = _clamp((1.0 - self._or_window_timing_protective) * ew * 2.5, 0.0, 8.0)

        return {
            "hours_wake_to_first": round(h_w2f, 2),
            "hours_last_to_bed": round(h_l2b, 2),
            "eating_window": round(ew, 2),
            "timing_penalty": round(timing_pen, 2),
            "duration_penalty": round(duration_pen, 2),
            "window_bonus": round(window_bonus, 2),
        }


# ---------------------------------------------------------------------------
# 4. LightPathway
# ---------------------------------------------------------------------------

@dataclass
class LightPathway:
    """Models light exposure effects on latency and next-morning alertness."""

    daytime_bright_light_hours: float = 1.0
    pre_bed_light_lux: float = 30.0
    night_light_minutes: float = 0.0

    _sol_min_per_log_lux: float = 30.0
    _reference_lux: float = 10.0

    def _sol_latency_penalty_min(self) -> float:
        ref_log = _log10_safe(self._reference_lux)
        bed_log = _log10_safe(self.pre_bed_light_lux + 1e-9)
        delta_log = max(0.0, bed_log - ref_log)
        return delta_log * self._sol_min_per_log_lux

    def _alertness_score(self) -> float:
        return _clamp(self.daytime_bright_light_hours / 2.0 * 100.0, 0.0, 100.0)

    def compute(self) -> Dict[str, float]:
        sol_min = self._sol_latency_penalty_min()
        latency_pen = _clamp((sol_min / 15.0) * 5.0, 0.0, 25.0)

        alertness_score = self._alertness_score()
        alertness_bonus = _clamp((alertness_score / 100.0) * 20.0, 0.0, 20.0)

        night_pen = _clamp((self.night_light_minutes / 30.0) * 3.0, 0.0, 12.0)

        return {
            "sol_latency_penalty_min": round(sol_min, 1),
            "latency_penalty_points": round(latency_pen, 2),
            "alertness_score": round(alertness_score, 1),
            "alertness_bonus": round(alertness_bonus, 2),
            "night_light_penalty": round(night_pen, 2),
        }


# ---------------------------------------------------------------------------
# 5. EveningDietModifier  (Soares et al. 2025 cross-pathway interaction)
# ---------------------------------------------------------------------------

@dataclass
class EveningDietModifier:
    """
    Models the Soares et al. (2025) finding that evening diet composition
    mediates the relationship between meal timing and sleep quality.

    This is NOT an independent pathway — it modifies the outputs of
    CaffeinePathway, AlcoholPathway, and MealTimingPathway.
    """

    evening_caffeine_mg: float = 0.0
    evening_alcohol_drinks: float = 0.0
    hours_last_eat_to_bed: float = 3.0
    screen_time_minutes: float = 0.0
    sensitivity_multiplier: float = 1.0  # personalized via Bayesian updater

    # Soares et al. (2025) standardized coefficients
    _de_disturbing_diet: float = 0.189
    _de_evening_latency_short: float = -0.126
    _ie_mediation: float = 0.013
    _de_screen_time: float = 0.001

    def compute(self) -> Dict:
        has_evening_caffeine = self.evening_caffeine_mg > 10.0
        has_evening_alcohol = self.evening_alcohol_drinks > 0.0

        diet_disturbing_score = 0.0
        if has_evening_caffeine:
            diet_disturbing_score += 0.5
        if has_evening_alcohol:
            diet_disturbing_score += 0.5

        # Direct effect of disturbing diet on quality (max ~8 pts penalty)
        diet_quality_penalty = diet_disturbing_score * self._de_disturbing_diet * 40.0
        diet_quality_penalty = _clamp(diet_quality_penalty * self.sensitivity_multiplier, 0.0, 8.0)

        # Evening latency interaction (mediation effect)
        short_latency = self.hours_last_eat_to_bed <= 2.0
        if short_latency and diet_disturbing_score > 0:
            mediation_penalty = diet_disturbing_score * self._ie_mediation * 40.0
            mediation_penalty = _clamp(mediation_penalty * self.sensitivity_multiplier, 0.0, 3.0)
        elif short_latency and diet_disturbing_score == 0:
            # Short latency with clean diet is PROTECTIVE
            mediation_penalty = self._de_evening_latency_short * 15.0  # negative = bonus
            mediation_penalty = _clamp(mediation_penalty, -4.0, 0.0)
        else:
            mediation_penalty = 0.0

        # Screen time penalty (max 4 pts)
        screen_penalty = _clamp(self.screen_time_minutes * self._de_screen_time * 0.5, 0.0, 4.0)

        return {
            "diet_disturbing_score": round(diet_disturbing_score, 2),
            "diet_quality_penalty": round(diet_quality_penalty, 2),
            "mediation_penalty": round(mediation_penalty, 2),
            "screen_penalty": round(screen_penalty, 2),
            "has_evening_caffeine": has_evening_caffeine,
            "has_evening_alcohol": has_evening_alcohol,
        }


# ---------------------------------------------------------------------------
# 6. SleepScoreCalculator
# ---------------------------------------------------------------------------

@dataclass
class SleepScoreCalculator:
    """Combines pathway outputs into a single 0-100 score."""

    caffeine_pathway: CaffeinePathway = field(default_factory=CaffeinePathway)
    alcohol_pathway: AlcoholPathway = field(default_factory=AlcoholPathway)
    meal_timing_pathway: MealTimingPathway = field(default_factory=MealTimingPathway)
    light_pathway: LightPathway = field(default_factory=LightPathway)
    evening_diet_modifier: EveningDietModifier = field(default_factory=EveningDietModifier)

    _max_duration: float = 30.0
    _max_quality: float = 30.0
    _max_timing: float = 20.0
    _max_alertness: float = 20.0

    def compute(self) -> Dict:
        caf = self.caffeine_pathway.compute()
        alc = self.alcohol_pathway.compute()
        meal = self.meal_timing_pathway.compute()
        light = self.light_pathway.compute()
        evening = self.evening_diet_modifier.compute()

        # --- Duration component (max 30) ---
        caf_dur_pen = _clamp(caf["duration_penalty_min"] / 120.0 * 20.0, 0.0, 20.0)
        meal_dur_pen = _clamp(meal["duration_penalty"] / 15.0 * 10.0, 0.0, 10.0)
        duration_score = _clamp(
            self._max_duration - caf_dur_pen - meal_dur_pen, 0.0, self._max_duration
        )

        # --- Quality component (max 30) ---
        alc_qual_pen = _clamp(alc["net_quality_penalty"] / 40.0 * 20.0, 0.0, 20.0)
        caf_qual_pen = _clamp(caf["quality_penalty"] / 20.0 * 10.0, 0.0, 10.0)
        quality_score = _clamp(
            self._max_quality - alc_qual_pen - caf_qual_pen, 0.0, self._max_quality
        )
        # Soares evening diet: apply direct diet quality penalty (max 5 pts)
        evening_qual_pen = _clamp(evening["diet_quality_penalty"] / 8.0 * 5.0, 0.0, 5.0)
        quality_score = _clamp(quality_score - evening_qual_pen, 0.0, self._max_quality)

        # --- Timing component (max 20) ---
        meal_tim_pen = _clamp(meal["timing_penalty"] / 15.0 * 12.0, 0.0, 12.0)
        meal_window_bonus = _clamp(meal["window_bonus"] / 8.0 * 4.0, 0.0, 4.0)
        light_lat_pen = _clamp(light["latency_penalty_points"] / 25.0 * 8.0, 0.0, 8.0)
        timing_score = _clamp(
            self._max_timing - meal_tim_pen + meal_window_bonus - light_lat_pen,
            0.0,
            self._max_timing,
        )
        # Soares mediation: negative = bonus (clean short latency), positive = penalty
        evening_timing_adj = _clamp(evening["mediation_penalty"] / 3.0 * 4.0, -4.0, 4.0)
        timing_score = _clamp(timing_score - evening_timing_adj, 0.0, self._max_timing)

        # --- Alertness component (max 20) ---
        alertness_bonus = light["alertness_bonus"]
        night_light_pen = _clamp(light["night_light_penalty"] / 12.0 * 5.0, 0.0, 5.0)
        alertness_score = _clamp(
            alertness_bonus - night_light_pen, 0.0, self._max_alertness
        )
        # Soares screen time penalty (max 3 pts)
        evening_screen_pen = _clamp(evening["screen_penalty"] / 4.0 * 3.0, 0.0, 3.0)
        alertness_score = _clamp(alertness_score - evening_screen_pen, 0.0, self._max_alertness)

        total_score = duration_score + quality_score + timing_score + alertness_score
        total_score = _clamp(total_score, 0.0, 100.0)

        breakdown = {
            "total_score": round(total_score, 1),
            "components": {
                "duration": {
                    "score": round(duration_score, 1),
                    "max": self._max_duration,
                    "caffeine_duration_penalty_min": caf["duration_penalty_min"],
                    "caffeine_residual_mg": caf["residual_mg"],
                    "caffeine_residual_cups": caf["residual_cups"],
                    "caffeine_effective_residual_cups": caf["effective_residual_cups"],
                    "caffeine_sensitivity_multiplier": caf["sensitivity_multiplier"],
                    "meal_timing_duration_penalty_pts": round(meal_dur_pen, 2),
                },
                "quality": {
                    "score": round(quality_score, 1),
                    "max": self._max_quality,
                    "alcohol_net_quality_penalty": alc["net_quality_penalty"],
                    "alcohol_raw_penalty": alc["raw_quality_penalty"],
                    "caffeine_alcohol_interaction_offset": alc["interaction_offset"],
                    "caffeine_quality_penalty": caf["quality_penalty"],
                    "evening_diet_quality_penalty": round(evening_qual_pen, 2),
                    "evening_diet_disturbing_score": evening["diet_disturbing_score"],
                },
                "timing": {
                    "score": round(timing_score, 1),
                    "max": self._max_timing,
                    "meal_timing_penalty_pts": round(meal_tim_pen, 2),
                    "meal_window_bonus_pts": round(meal_window_bonus, 2),
                    "light_latency_penalty_min": light["sol_latency_penalty_min"],
                    "light_latency_penalty_pts": round(light_lat_pen, 2),
                    "hours_wake_to_first_meal": meal["hours_wake_to_first"],
                    "hours_last_meal_to_bed": meal["hours_last_to_bed"],
                    "eating_window_hours": meal["eating_window"],
                    "evening_mediation_adjustment": round(evening_timing_adj, 2),
                },
                "alertness": {
                    "score": round(alertness_score, 1),
                    "max": self._max_alertness,
                    "daytime_alertness_score": light["alertness_score"],
                    "alertness_bonus_pts": round(alertness_bonus, 2),
                    "night_light_penalty_pts": round(night_light_pen, 2),
                    "night_light_minutes": self.light_pathway.night_light_minutes,
                    "screen_time_penalty_pts": round(evening_screen_pen, 2),
                },
            },
            "evening_diet_modifier": {
                "diet_disturbing_score": evening["diet_disturbing_score"],
                "diet_quality_penalty": evening["diet_quality_penalty"],
                "mediation_penalty": evening["mediation_penalty"],
                "screen_penalty": evening["screen_penalty"],
                "has_evening_caffeine": evening["has_evening_caffeine"],
                "has_evening_alcohol": evening["has_evening_alcohol"],
            },
        }

        return breakdown
