"""
main.py
-------
CLI entry point for the shipment route recommender.

Usage:
    python main.py --shipment SHP001        # recommend + explain one shipment
                                              # (includes P10/median/P90 cost
                                              # exposure under delay uncertainty)
    python main.py --whatif SHP001           # show recommendation under all
                                              # 4 priority types for one shipment
    python main.py --all                     # recommend for all shipments,
                                              # write outputs/recommendations.json,
                                              # print evaluation summary
"""

import argparse
import json
from pathlib import Path

from src.scoring import score_routes, DEFAULT_WEIGHTS
from src.explain import explain_recommendation
from src.sensitivity import robustness_check
from src.evaluate import evaluate_dataset
from src.uncertainity import simulate_route_outcomes

DATA_PATH = Path(__file__).parent / "data" / "shipments.json"
OUTPUT_DIR = Path(__file__).parent / "outputs"


def load_shipments():
    with open(DATA_PATH) as f:
        return json.load(f)


def recommend_one(shipment):
    scored = score_routes(shipment)
    explanation = explain_recommendation(shipment, scored)
    robustness = robustness_check(shipment)
    return scored, explanation, robustness


def run_single(shipment_id):
    shipments = load_shipments()
    shipment = next((s for s in shipments if s["shipment_id"] == shipment_id), None)
    if shipment is None:
        print(f"Shipment {shipment_id} not found.")
        return

    scored, explanation, robustness = recommend_one(shipment)
    print(explanation)
    print()
    print(
        f"Recommendation stability under +/-15% weight perturbation: "
        f"{robustness['stability']*100:.0f}% of trials agree with the base pick "
        f"({robustness['n_trials']} trials)."
    )

    best = scored[0]
    sim = simulate_route_outcomes(best.route)
    print()
    print(
        f"Cost exposure under delay uncertainty for {sim['route_id']} "
        f"({sim['n_trials']} simulated trials):"
    )
    print(f"  P10 (best-case-ish): ${sim['p10_cost']:,.0f}")
    print(f"  Median:              ${sim['median_cost']:,.0f}")
    print(f"  P90 (unlucky case):  ${sim['p90_cost']:,.0f}")
    print(f"  Simulated delay occurred in {sim['pct_trials_with_delay']:.1f}% of trials")


def run_whatif(shipment_id):
    """Show how the recommendation changes if the shipment had a different
    stated priority - makes the weight-driven trade-off logic explicit."""
    shipments = load_shipments()
    shipment = next((s for s in shipments if s["shipment_id"] == shipment_id), None)
    if shipment is None:
        print(f"Shipment {shipment_id} not found.")
        return

    print(f"What-if priority comparison for {shipment_id} "
          f"(actual priority: {shipment['priority']}):\n")
    for priority_name, weights in DEFAULT_WEIGHTS.items():
        scored = score_routes(shipment, weights)
        best = scored[0]
        marker = " <- actual priority" if priority_name == shipment["priority"] else ""
        print(
            f"  {priority_name:<15} -> {best.route['route_id']:<12} "
            f"${best.route['cost_usd']:>8,.0f}  {best.route['transit_time_days']:>5.1f}d  "
            f"risk {best.effective_risk*100:>4.0f}%{marker}"
        )


def run_all():
    shipments = load_shipments()
    OUTPUT_DIR.mkdir(exist_ok=True)

    results = []
    for shipment in shipments:
        scored, explanation, robustness = recommend_one(shipment)
        best = scored[0]
        results.append({
            "shipment_id": shipment["shipment_id"],
            "origin": shipment["origin"],
            "destination": shipment["destination"],
            "priority": shipment["priority"],
            "recommended_route": best.route["route_id"],
            "cost_usd": best.route["cost_usd"],
            "transit_time_days": best.route["transit_time_days"],
            "effective_risk": round(best.effective_risk, 3),
            "weighted_score": round(best.weighted_score, 4),
            "stability": round(robustness["stability"], 3),
            "explanation": explanation,
        })

    out_file = OUTPUT_DIR / "recommendations.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} recommendations -> {out_file}")

    print("\nRunning evaluation across the dataset...")
    eval_summary = evaluate_dataset(shipments)
    eval_file = OUTPUT_DIR / "evaluation_summary.txt"
    with open(eval_file, "w") as f:
        for k, v in eval_summary.items():
            line = f"{k}: {v}"
            print(line)
            f.write(line + "\n")
    print(f"\nWrote evaluation summary -> {eval_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shipment route recommender")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--shipment", help="Shipment ID to recommend a route for, e.g. SHP001")
    group.add_argument("--all", action="store_true", help="Run for all shipments and evaluate")
    group.add_argument("--whatif", help="Show recommendation under all 4 priority types for a shipment")
    args = parser.parse_args()

    if args.shipment:
        run_single(args.shipment)
    elif args.whatif:
        run_whatif(args.whatif)
    else:
        run_all()