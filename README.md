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

```
safiri_route_optimizer/
├── data/
│   ├── generate_data.py     # synthetic dataset generator
│   └── shipments.json       # 40 shipments, 3-5 routes each (input dataset)
├── src/
│   ├── scoring.py           # weighted multi-criteria scoring engine
│   ├── explain.py           # human-readable explanation generator
│   ├── sensitivity.py       # weight-perturbation robustness check
│   ├── uncertainty.py       # Monte Carlo delay-cost uncertainty simulation
│   └── evaluate.py          # Pareto-check + baseline comparison
├── main.py                  # CLI entry point
└── requirements.txt
```
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

**Recommend a route for a single shipment** - prints the full explanation,
a stability check, and a delay-cost uncertainty simulation:

```bash
python main.py --shipment SHP001
```

**Compare how the recommendation changes under each priority type**, for
one shipment - makes the weight-driven trade-off logic explicit:

```bash
python main.py --whatif SHP002
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
   (dollars, days, percentage points of risk) - not raw scores. Also flags
   "close calls" when the top two options are separated by a small margin
   in weighted score, since those deserve a human look rather than a
   silent automatic pick.

3. **Sensitivity (`sensitivity.py`)**: perturbs the weight vector randomly
   (+/-15%, 200 trials by default) and reports what fraction of trials
   still pick the same route.

4. **Uncertainty (`uncertainty.py`)**: delay_probability is a forecast, not
   a measured fact. This module runs a Monte Carlo simulation (2000 trials
   by default) that jitters the delay probability and samples a random
   delay severity, reporting P10/median/P90 cost exposure plus the percent
   of trials that experienced a delay at all - so a route with a very low
   delay probability can honestly show "no meaningful spread" instead of a
   misleadingly precise-looking range.

5. **Evaluation (`evaluate.py`)**: since there's no ground truth for
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
- A flat $1,500 assumed cost-of-delay, used for the "expected total
  exposure" figure in explanations and as the base severity for the
  uncertainty simulation (not used in the core scoring itself).
- Close-call threshold is a 15% relative margin in weighted score, chosen
  as a reasonable default rather than tuned against real outcomes.

## Limitations

- Weights per priority category are hand-set, not learned or calibrated
  against real shipper behavior.
- Risk sub-indicators (congestion/geopolitical/weather) are synthetic and
  not tied to any live data feed.
- The "balanced" priority category, by design, has no dominant weight and
  can show lower recommendation stability - this is expected behavior, not
  a bug. It can also converge with another priority type's pick when one
  route is extreme enough on a single dimension (e.g. much faster than
  every alternative) to win even under a near-even weight split - a known
  characteristic of weighted-sum scoring, not an error.
- The uncertainty simulation only varies delay likelihood and severity; it
  does not model correlated risk across sub-indicators (e.g. geopolitical
  risk spiking congestion at the same hub).

