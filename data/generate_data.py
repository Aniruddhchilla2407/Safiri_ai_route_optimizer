"""
generate_data.py
-----------------
Generates a synthetic dataset of shipments, each with 3-5 candidate routes.

Design notes (documented for the report):
- Ports/hubs are drawn from a fixed pool of realistic global logistics nodes.
- For each shipment we pick an origin/destination pair, then generate several
  route "philosophies": a direct/fast route, a cheap-but-slow route, a
  risk-averse detour, and 1-2 "middle ground" routes. This mirrors the fact
  that in real logistics, alternative routings usually reflect genuine
  strategic trade-offs (e.g. avoiding a canal/strait, routing via a cheaper
  but more congested transshipment hub) rather than pure random noise.
- cost and transit_time are anti-correlated with a controllable noise term,
  so that (on average) faster routes cost more - but not always, to keep the
  problem non-trivial.
- risk is modeled as three sub-indicators (congestion, geopolitical, weather)
  which are combined into a single risk_score in [0, 1]. Keeping the
  sub-indicators lets the explanation layer say *why* a route is risky.
- delay_probability is correlated with risk_score plus its own noise, since
  in reality delay likelihood is driven by (but not identical to) the risk
  factors.
- Each shipment is tagged with a "priority" (cost_sensitive / time_sensitive
  / risk_averse / balanced) representing the shipper's stated preference,
  which the scoring engine uses to set weights. This simulates the realistic
  scenario where different customers/cargo types (e.g. perishables vs. bulk
  commodities) care about different things.
"""

import json
import random
from pathlib import Path

random.seed(42)  # reproducibility

PORTS = [
    "Shanghai", "Singapore", "Rotterdam", "Los Angeles", "Dubai (Jebel Ali)",
    "Antwerp", "Busan", "Hamburg", "Mumbai (Nhava Sheva)", "New York",
    "Santos", "Colombo", "Piraeus", "Felixstowe", "Ho Chi Minh City",
    "Durban", "Alexandria", "Vancouver", "Chennai", "Hong Kong",
]

HUBS = [
    "Suez Canal", "Panama Canal", "Malacca Strait", "Gibraltar Strait",
    "Colombo Transshipment", "Jebel Ali Transshipment", "Cape of Good Hope",
    "Bosphorus Strait", "Malta Freeport",
]

PRIORITIES = ["cost_sensitive", "time_sensitive", "risk_averse", "balanced"]

CARGO_TYPES = [
    "Electronics", "Perishable Produce", "Automotive Parts", "Textiles",
    "Pharmaceuticals", "Bulk Grain", "Furniture", "Chemicals",
    "Consumer Goods", "Machinery",
]

# Cargo types that plausibly skew a shipment's stated priority
CARGO_PRIORITY_BIAS = {
    "Perishable Produce": "time_sensitive",
    "Pharmaceuticals": "risk_averse",
    "Bulk Grain": "cost_sensitive",
    "Chemicals": "risk_averse",
    "Electronics": "time_sensitive",
}


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def gen_route(route_id, base_distance_factor, archetype):
    """
    archetype in {"fast", "cheap", "safe", "middle"} biases the generated
    attributes to represent a genuine strategic alternative rather than
    random noise.
    """
    hubs_used = random.sample(HUBS, k=random.choice([0, 1, 1, 2]))

    if archetype == "fast":
        transit_time = base_distance_factor * random.uniform(0.65, 0.8)
        cost = base_distance_factor * random.uniform(95, 115)
        congestion = random.uniform(0.2, 0.5)
        geo = random.uniform(0.1, 0.4)
        weather = random.uniform(0.1, 0.4)
    elif archetype == "cheap":
        transit_time = base_distance_factor * random.uniform(1.1, 1.4)
        cost = base_distance_factor * random.uniform(55, 75)
        congestion = random.uniform(0.3, 0.6)
        geo = random.uniform(0.1, 0.4)
        weather = random.uniform(0.2, 0.5)
    elif archetype == "safe":
        transit_time = base_distance_factor * random.uniform(0.95, 1.25)
        cost = base_distance_factor * random.uniform(85, 105)
        congestion = random.uniform(0.05, 0.25)
        geo = random.uniform(0.02, 0.15)
        weather = random.uniform(0.05, 0.25)
    else:  # middle
        transit_time = base_distance_factor * random.uniform(0.85, 1.05)
        cost = base_distance_factor * random.uniform(75, 95)
        congestion = random.uniform(0.2, 0.45)
        geo = random.uniform(0.1, 0.35)
        weather = random.uniform(0.15, 0.4)

    risk_score = clamp(0.45 * congestion + 0.35 * geo + 0.2 * weather)
    # delay probability correlates with risk but has its own noise term
    delay_probability = clamp(0.55 * risk_score + random.uniform(-0.08, 0.15))

    return {
        "route_id": route_id,
        "hubs": hubs_used,
        "cost_usd": round(cost, 2),
        "transit_time_days": round(transit_time, 1),
        "delay_probability": round(delay_probability, 3),
        "risk_indicators": {
            "congestion": round(congestion, 3),
            "geopolitical": round(geo, 3),
            "weather": round(weather, 3),
        },
        "risk_score": round(risk_score, 3),
        "archetype": archetype,  # kept for dataset transparency/debugging
    }


def gen_shipment(shipment_id):
    origin, destination = random.sample(PORTS, 2)
    cargo_type = random.choice(CARGO_TYPES)
    priority = CARGO_PRIORITY_BIAS.get(cargo_type)
    if priority is None or random.random() < 0.3:
        priority = random.choice(PRIORITIES)

    base_distance_factor = random.uniform(8, 35)  # proxy for distance/complexity
    n_routes = random.choice([3, 3, 4, 4, 5])
    archetypes = ["fast", "cheap", "safe"] + random.choices(
        ["middle", "fast", "cheap", "safe"], k=max(0, n_routes - 3)
    )
    random.shuffle(archetypes)

    routes = [
        gen_route(f"{shipment_id}-R{i+1}", base_distance_factor, arch)
        for i, arch in enumerate(archetypes[:n_routes])
    ]

    return {
        "shipment_id": shipment_id,
        "origin": origin,
        "destination": destination,
        "cargo_type": cargo_type,
        "priority": priority,
        "routes": routes,
    }


def main(n_shipments=40, out_path="shipments.json"):
    shipments = [gen_shipment(f"SHP{str(i+1).zfill(3)}") for i in range(n_shipments)]
    out_file = Path(__file__).parent / out_path
    with open(out_file, "w") as f:
        json.dump(shipments, f, indent=2)
    print(f"Generated {n_shipments} shipments -> {out_file}")


if __name__ == "__main__":
    main()