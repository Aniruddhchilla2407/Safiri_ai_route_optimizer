"""
explain.py
----------
Turns the scored routes into a human-readable explanation for a logistics
operator: what was picked, what was passed over, and *why*, expressed in
terms the operator already thinks in (dollars, days, % risk) rather than
raw normalized scores.
"""

from .scoring import DEFAULT_WEIGHTS


def _pct_diff(a, b):
    """Percentage change from b to a, guarding against div-by-zero."""
    if b == 0:
        return float("inf") if a != 0 else 0.0
    return (a - b) / b * 100


def explain_recommendation(shipment: dict, scored_routes: list, weights: dict = None) -> str:
    if weights is None:
        weights = DEFAULT_WEIGHTS.get(shipment["priority"], DEFAULT_WEIGHTS["balanced"])

    best = scored_routes[0]
    lines = []
    lines.append(
        f"Shipment {shipment['shipment_id']} ({shipment['origin']} -> "
        f"{shipment['destination']}, cargo: {shipment['cargo_type']}, "
        f"priority: {shipment['priority']})"
    )
    lines.append(
        f"Weights applied -> cost: {weights['cost']:.0%}, "
        f"time: {weights['time']:.0%}, risk: {weights['risk']:.0%}"
    )
    lines.append("")
    lines.append(
        f"RECOMMENDED: {best.route['route_id']} "
        f"(${best.route['cost_usd']:,.0f}, {best.route['transit_time_days']:.1f} days, "
        f"{best.effective_risk*100:.0f}% effective risk, "
        f"est. total exposure incl. delay risk ~${best.expected_cost:,.0f})"
    )

    if len(scored_routes) > 1:
        runner_up = scored_routes[1]
        cost_diff = _pct_diff(best.route["cost_usd"], runner_up.route["cost_usd"])
        time_diff = _pct_diff(best.route["transit_time_days"], runner_up.route["transit_time_days"])
        # Risk is already a percentage (0-1), so report it as a percentage-POINT
        # difference rather than a relative % change - relative % on a small
        # base (e.g. 9% -> 38%) produces misleadingly huge numbers ("335%
        # higher risk") that don't match how risk is displayed elsewhere.
        risk_diff_points = (best.effective_risk - runner_up.effective_risk) * 100

        reasons = []
        deltas = {
            "cost": (cost_diff, weights["cost"], "%"),
            "time": (time_diff, weights["time"], "%"),
            "risk": (risk_diff_points, weights["risk"], "pp"),
        }
        # Dimension(s) where winner is worse (a genuine trade-off) vs. better
        worse_dims = {k: v for k, v in deltas.items() if v[0] > 1}
        better_dims = {k: v for k, v in deltas.items() if v[0] < -1}

        if better_dims:
            # List EVERY dimension where the winner is better, not just the
            # single strongest one - a route that wins on two axes should
            # get credit for both, not just the most heavily-weighted one.
            for dim_name, (diff, w, unit_sym) in sorted(
                better_dims.items(), key=lambda kv: abs(kv[1][0]) * kv[1][1], reverse=True
            ):
                unit = {"cost": "cheaper", "time": "faster", "risk": "lower effective risk"}[dim_name]
                reasons.append(f"it is {abs(diff):.0f}{unit_sym} {unit} than the runner-up ({runner_up.route['route_id']})")

        if worse_dims:
            for dim_name, (diff, w, unit_sym) in worse_dims.items():
                unit = {"cost": "more expensive", "time": "slower", "risk": "higher effective risk"}[dim_name]
                reasons.append(
                    f"despite being {diff:.0f}{unit_sym} {unit} than {runner_up.route['route_id']}, "
                    f"this is outweighed given the shipment's {shipment['priority']} priority "
                    f"(weight on {dim_name}: {w:.0%})"
                )

        if reasons:
            lines.append("")
            lines.append("Why this route over the next-best alternative " + f"({runner_up.route['route_id']}):")
            for r in reasons:
                lines.append(f"  - {r}")

        lines.append(
            f"  - Overall weighted score: {best.weighted_score:.3f} vs "
            f"{runner_up.weighted_score:.3f} for the runner-up (lower is better)"
        )

        # Flag close calls explicitly: if the top two options are separated
        # by a small margin, the "right" answer is genuinely uncertain and
        # worth a human look, not just an automatic pick.
        CLOSE_CALL_MARGIN = 0.15  # relative margin threshold, documented assumption
        margin = (runner_up.weighted_score - best.weighted_score) / max(runner_up.weighted_score, 1e-9)
        if margin < CLOSE_CALL_MARGIN:
            lines.append("")
            lines.append(
                f"  NOTE: this is a close call - {best.route['route_id']} and "
                f"{runner_up.route['route_id']} are separated by only "
                f"{margin*100:.0f}% in weighted score. Consider a manual review "
                f"(see stability check below)."
            )

    lines.append("")
    lines.append("All options considered:")
    for s in scored_routes:
        marker = "-> " if s.rank == 0 else "   "
        lines.append(
            f"{marker}{s.route['route_id']:<12} "
            f"${s.route['cost_usd']:>9,.0f}  "
            f"{s.route['transit_time_days']:>5.1f}d  "
            f"risk {s.effective_risk*100:>4.0f}%  "
            f"score {s.weighted_score:.3f}"
        )
    return "\n".join(lines)