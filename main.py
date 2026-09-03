"""
main.py
-------
CLI entry point for the shipment route recommender.

Usage:
    python main.py --shipment SHP001        # recommend + explain one shipment
    python main.py --all                    # recommend for all shipments,
                                              # write outputs/recommendations.json,
                                              # print evaluation summary
"""

import argparse
import json
from pathlib import Path

from src.scoring import score_routes
from src.explain import explain_recommendation
from src.sensitivity import robustness_check
from src.evaluate import evaluate_dataset

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
    args = parser.parse_args()

    if args.shipment:
        run_single(args.shipment)
    else:
        run_all()