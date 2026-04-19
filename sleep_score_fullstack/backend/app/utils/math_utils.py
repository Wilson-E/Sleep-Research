"""Small numeric helpers shared across the scoring and simulation services."""


def clamp(x: float, lo: float, hi: float) -> float:
    """Return x constrained to the inclusive range [lo, hi]."""
    return max(lo, min(hi, x))
