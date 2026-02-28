"""Client targeting and recipe filter ranges for the orchestrator."""
from typing import Any


def _percentile_range(values: list[float], low_pct: float = 25, high_pct: float = 75) -> tuple[float, float]:
    """Return (low, high) at given percentiles. Uses quartiles by default for a middle band."""
    if not values:
        return (0.0, 0.0)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    lo_idx = max(0, int(n * low_pct / 100))
    hi_idx = min(n - 1, int(n * high_pct / 100))
    if lo_idx > hi_idx:
        lo_idx, hi_idx = hi_idx, lo_idx
    return (sorted_vals[lo_idx], sorted_vals[hi_idx])


def compute_target_ranges(recipes: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze distribution of prep_time and prestige across recipes, then define ranges
    that select a reasonable subset (not excessive). Uses quartiles (25th–75th) to
    focus on the central band of each dimension.
    """
    if not recipes:
        return {
            "target_client": "default",
            "prep_time_min": 0,
            "prep_time_max": 30,
            "prestige_min": 0,
            "prestige_max": 3,
        }

    prep_times = [r.get("prep_time", 0) for r in recipes if "prep_time" in r]
    prestiges = [r.get("prestige", 0) for r in recipes if "prestige" in r]

    if not prep_times:
        prep_times = [0]
    if not prestiges:
        prestiges = [0]

    prep_min, prep_max = _percentile_range(prep_times)
    prestige_min, prestige_max = _percentile_range(prestiges)

    # Ensure non-empty range (avoid prep_min == prep_max excluding all)
    if prep_min == prep_max:
        prep_min = max(0, prep_min - 1)
        prep_max = prep_max + 1
    if prestige_min == prestige_max:
        prestige_min = max(0, prestige_min - 1)
        prestige_max = prestige_max + 1

    # Count recipes in range to verify we get a reasonable subset
    in_range = sum(
        1
        for r in recipes
        if prep_min <= r.get("prep_time", 0) <= prep_max
        and prestige_min <= r.get("prestige", 0) <= prestige_max
    )

    return {
        "target_client": "distribution_based",
        "prep_time_min": int(prep_min),
        "prep_time_max": int(prep_max),
        "prestige_min": int(prestige_min),
        "prestige_max": int(prestige_max),
        "recipes_in_range": in_range,
        "total_recipes": len(recipes),
    }
