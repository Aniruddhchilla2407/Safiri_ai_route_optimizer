"""
evaluate.py
-----------
Since there's no ground-truth "correct route" for a synthetic dataset, we
evaluate the *decision framework* itself:

1. Pareto-efficiency check: a trustworthy recommender should never recommend
   a route that is strictly dominated by another available option. We
   report the % of shipments where this holds.

2. Baseline comparison: how often does the weighted recommendation differ
   from the naive "cheapest", "fastest", and "lowest risk" baselines?
   Quantifies the average trade-off (extra $ / days / risk) accepted
   relative to each single-metric baseline.

3. Stability summary: aggregate sensitivity.robustness_check results across
   the dataset to report what fraction of recommendations are "robust"
   vs. "close calls".
"""

from .scoring import score_routes, effective_risk, is_pareto_dominated
from .sensitivity import robustness_check


def evaluate_dataset(shipments: list, stability_threshold: float = 0.7) -> dict:
    n = len(shipments)
    dominated_count = 0
    cost_deltas, time_deltas, risk_deltas = [], [], []
    agree_cheapest = agree_fastest = agree_safest = 0
    stabilities = []

    for shipment in shipments:
        scored = score_routes(shipment)
        best = scored[0]

        if is_pareto_dominated(best.route, shipment["routes"]):
            dominated_count += 1

        cheapest = min(shipment["routes"], key=lambda r: r["cost_usd"])
        fastest = min(shipment["routes"], key=lambda r: r["transit_time_days"])
        safest = min(shipment["routes"], key=lambda r: effective_risk(r))

        if best.route["route_id"] == cheapest["route_id"]:
            agree_cheapest += 1
        else:
            cost_deltas.append(best.route["cost_usd"] - cheapest["cost_usd"])

        if best.route["route_id"] == fastest["route_id"]:
            agree_fastest += 1
        else:
            time_deltas.append(best.route["transit_time_days"] - fastest["transit_time_days"])

        if best.route["route_id"] == safest["route_id"]:
            agree_safest += 1
        else:
            risk_deltas.append(effective_risk(best.route) - effective_risk(safest))

        rob = robustness_check(shipment, n_trials=100)
        stabilities.append(rob["stability"])

    avg = lambda lst: (sum(lst) / len(lst)) if lst else 0.0
    robust_fraction = sum(1 for s in stabilities if s >= stability_threshold) / n

    return {
        "n_shipments": n,
        "pct_non_dominated_recommendations": 100 * (1 - dominated_count / n),
        "pct_matches_cheapest_baseline": 100 * agree_cheapest / n,
        "pct_matches_fastest_baseline": 100 * agree_fastest / n,
        "pct_matches_safest_baseline": 100 * agree_safest / n,
        "avg_extra_cost_vs_cheapest_when_differs": avg(cost_deltas),
        "avg_extra_days_vs_fastest_when_differs": avg(time_deltas),
        "avg_extra_effective_risk_vs_safest_when_differs": avg(risk_deltas),
        "avg_recommendation_stability": avg(stabilities),
        "pct_robust_recommendations": 100 * robust_fraction,
        "stability_threshold_used": stability_threshold,
    }