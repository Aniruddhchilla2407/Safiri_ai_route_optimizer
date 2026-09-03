"""
scoring.py
----------
Weighted multi-criteria decision analysis (MCDA) engine for scoring routes.

Design rationale:

1. Metrics considered: cost, transit_time, and an "effective risk" figure
   that blends delay_probability with risk_score. We deliberately do NOT
   treat delay_probability and risk_score as fully separate weighted
   criteria, because they are correlated by construction (risk drives
   delay) and double-weighting them would silently over-penalize risk
   relative to the shipper's stated intent. Instead:
       effective_risk = 0.6 * risk_score + 0.4 * delay_probability
   which keeps risk as a single interpretable axis while still reflecting
   both "how likely is a problem" (delay_probability) and "how bad could it
   be" (risk_score, e.g. geopolitical/congestion exposure).

2. Normalization: min-max normalization *within each shipment's route set*
   (not globally), because "cost" is only meaningful relative to the
   alternatives available for that specific shipment. If a route set has
   zero variance on some metric, that metric contributes 0 to every route's
   score (no information to discriminate on).

3. Weights: derived from a `priority` label representing the shipper's
   stated preference (cost_sensitive / time_sensitive / risk_averse /
   balanced). A custom weight vector can also be passed directly, which
   supports sensitivity analysis (see sensitivity.py).

4. Score: weighted sum of normalized "badness" (0 = best route on that
   metric, 1 = worst). Lower total score = better route. Transparent and
   auditable, unlike an opaque ML ranker.

5. Secondary interpretable metric - expected total cost:
       expected_cost = cost_usd + delay_probability * DELAY_COST_CONSTANT
   Translates risk into a monetary proxy for operator sanity-checking.
   NOT used in scoring itself, since collapsing everything into one dollar
   figure would hide the actual trade-off being made.
"""

from dataclasses import dataclass

DEFAULT_WEIGHTS = {
    "cost_sensitive": {"cost": 0.60, "time": 0.20, "risk": 0.20},
    "time_sensitive": {"cost": 0.20, "time": 0.60, "risk": 0.20},
    "risk_averse":    {"cost": 0.15, "time": 0.20, "risk": 0.65},
    "balanced":       {"cost": 0.34, "time": 0.33, "risk": 0.33},
}

# Assumed flat cost (USD) of a delay event, used only for the human-readable
# "expected cost" side metric shown in explanations - NOT used in scoring.
DELAY_COST_CONSTANT = 1500.0


def effective_risk(route):
    return 0.6 * route["risk_score"] + 0.4 * route["delay_probability"]


def expected_cost(route):
    return route["cost_usd"] + route["delay_probability"] * DELAY_COST_CONSTANT


def _minmax_normalize(values):
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


@dataclass
class ScoredRoute:
    route: dict
    norm_cost: float
    norm_time: float
    norm_risk: float
    weighted_score: float
    expected_cost: float
    effective_risk: float
    rank: int = -1


def score_routes(shipment: dict, weights: dict = None) -> list:
    """
    Returns a list of ScoredRoute, sorted best (rank 0) to worst.
    `weights` overrides the priority-derived defaults if provided
    (used for sensitivity analysis / what-if scenarios).
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS.get(shipment["priority"], DEFAULT_WEIGHTS["balanced"])

    routes = shipment["routes"]
    costs = [r["cost_usd"] for r in routes]
    times = [r["transit_time_days"] for r in routes]
    risks = [effective_risk(r) for r in routes]

    norm_costs = _minmax_normalize(costs)
    norm_times = _minmax_normalize(times)
    norm_risks = _minmax_normalize(risks)

    scored = []
    for r, nc, nt, nr, eff_r in zip(routes, norm_costs, norm_times, norm_risks, risks):
        weighted_score = (
            weights["cost"] * nc + weights["time"] * nt + weights["risk"] * nr
        )
        scored.append(
            ScoredRoute(
                route=r,
                norm_cost=nc,
                norm_time=nt,
                norm_risk=nr,
                weighted_score=weighted_score,
                expected_cost=expected_cost(r),
                effective_risk=eff_r,
            )
        )

    scored.sort(key=lambda s: s.weighted_score)
    for i, s in enumerate(scored):
        s.rank = i
    return scored


def is_pareto_dominated(candidate: dict, others: list) -> bool:
    """
    A route is Pareto-dominated if some other route is at least as good on
    cost, time, AND effective risk, and strictly better on at least one.
    Used by evaluate.py as a sanity check on recommendations.
    """
    c_cost, c_time, c_risk = (
        candidate["cost_usd"],
        candidate["transit_time_days"],
        effective_risk(candidate),
    )
    for o in others:
        if o["route_id"] == candidate["route_id"]:
            continue
        o_cost, o_time, o_risk = (
            o["cost_usd"],
            o["transit_time_days"],
            effective_risk(o),
        )
        at_least_as_good = o_cost <= c_cost and o_time <= c_time and o_risk <= c_risk
        strictly_better = o_cost < c_cost or o_time < c_time or o_risk < c_risk
        if at_least_as_good and strictly_better:
            return True
    return False