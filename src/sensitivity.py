"""
sensitivity.py
--------------
Answers: "how confident should we be in this recommendation?"

Approach: perturb the weight vector randomly within +/-`spread` of its
original values (re-normalized to sum to 1), re-score the routes, and check
how often the same route still wins. This addresses the assignment's
"sensitivity of decisions to parameter changes" challenge: a recommendation
that flips under small weight changes is a "close call" worth a human look;
one that's stable across large perturbations is a safe automatic decision.
"""

import random

from .scoring import DEFAULT_WEIGHTS, score_routes


def _perturb_weights(weights: dict, spread: float) -> dict:
    perturbed = {
        k: max(0.01, v + random.uniform(-spread, spread)) for k, v in weights.items()
    }
    total = sum(perturbed.values())
    return {k: v / total for k, v in perturbed.items()}


def robustness_check(shipment: dict, n_trials: int = 200, spread: float = 0.15) -> dict:
    base_weights = DEFAULT_WEIGHTS.get(shipment["priority"], DEFAULT_WEIGHTS["balanced"])
    base_winner = score_routes(shipment, base_weights)[0].route["route_id"]

    win_counts = {}
    for _ in range(n_trials):
        w = _perturb_weights(base_weights, spread)
        winner = score_routes(shipment, w)[0].route["route_id"]
        win_counts[winner] = win_counts.get(winner, 0) + 1

    stability = win_counts.get(base_winner, 0) / n_trials
    return {
        "shipment_id": shipment["shipment_id"],
        "base_winner": base_winner,
        "stability": stability,
        "win_counts": win_counts,
        "n_trials": n_trials,
        "spread": spread,
    }