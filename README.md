# Safiri AI - Shipment Route Recommender

A decision-support system that recommends the most suitable shipment route
from a set of alternatives, balancing **cost**, **transit time**, and
**risk**, and explaining the recommendation in plain terms.

## Problem

Given a shipment with several candidate routes (each with cost, transit
time, delay probability, and risk indicators), recommend the route that
best fits the shipment's priority (cost_sensitive / time_sensitive /
risk_averse / balanced) - and explain *why* that route was chosen over the
alternatives.

## Project structure
safiri_route_optimizer/
├── data/
│ ├── generate_data.py # synthetic dataset generator
│ └── shipments.json # 40 shipments, 3-5 routes each (input dataset)
├── src/
│ ├── scoring.py # weighted multi-criteria scoring engine
│ ├── explain.py # human-readable explanation generator
│ ├── sensitivity.py # weight-perturbation robustness check
│ └── evaluate.py # Pareto-check + baseline comparison
├── main.py # CLI entry point
├── requirements.txt
└── report/ # technical report (written after evaluation)

## Setup

No external dependencies - Python 3.8+ standard library only.

```bash
cd safiri_route_optimizer
```

(Optional) regenerate the dataset with a different seed/size by editing
`data/generate_data.py` and running:

```bash
python data/generate_data.py
```

## Usage

**Recommend a route for a single shipment** (prints a full explanation):

```bash
python main.py --shipment SHP001
```

**Run the recommender across the whole dataset**, write
`outputs/recommendations.json`, and print an evaluation summary:

```bash
python main.py --all
```

## How it works

1. **Scoring (`scoring.py`)**: for each shipment, cost/time/risk are
   min-max normalized *within that shipment's route set*, then combined
   into a weighted score. Weights are derived from the shipment's stated
   `priority`. Lower score = better route.

2. **Explanation (`explain.py`)**: compares the winning route to the
   runner-up across all three dimensions, in the shipper's own terms
   (dollars, days, percentage points of risk) - not raw scores.

3. **Sensitivity (`sensitivity.py`)**: perturbs the weight vector randomly
   (+/-15%, 200 trials by default) and reports what fraction of trials
   still pick the same route. This flags "close calls" vs. robust
   recommendations.

4. **Evaluation (`evaluate.py`)**: since there's no ground truth for
   synthetic data, the framework is evaluated on:
   - **Pareto-efficiency**: recommendations should never be strictly
     dominated by another available route (target: 100%).
   - **Divergence from naive baselines** (always-cheapest,
     always-fastest, always-safest) - demonstrates genuine multi-objective
     trade-off reasoning rather than a single-metric rule.
   - **Average stability** across the dataset.

## Assumptions

- Synthetic dataset (documented in `generate_data.py`); no real carrier
  data used.
- `effective_risk = 0.6 * risk_score + 0.4 * delay_probability` - a single
  risk axis combining severity and likelihood.
- A flat $1,500 assumed cost-of-delay, used only for the side "expected
  total exposure" figure shown in explanations (not used in scoring).

## Limitations

- Weights per priority category are hand-set, not learned or calibrated
  against real shipper behavior.
- Risk sub-indicators (congestion/geopolitical/weather) are synthetic and
  not tied to any live data feed.
- The "balanced" priority category, by design, has no dominant weight and
  can show lower recommendation stability - this is expected behavior, not
  a bug.