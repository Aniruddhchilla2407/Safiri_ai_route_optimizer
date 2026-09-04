"""
uncertainty.py
--------------
Quantifies the assignment's "uncertainty in delay or risk estimates"
challenge: rather than treating delay_probability as a fixed point
estimate, this module runs a Monte Carlo simulation that samples plausible
delay outcomes for a route and reports a range (P10-P90) for total cost
exposure, instead of a single number that hides how uncertain that number
actually is.

Approach:
- Each trial samples a "delay occurs" event using the route's stated
  delay_probability, with the probability itself jittered by +/-`prob_noise`
  to reflect that the input estimate is itself uncertain (it's a forecast,
  not a measured fact).
- If a delay occurs, a random severity multiplier is applied to the flat
  DELAY_COST_CONSTANT used elsewhere, so a "delay" isn't always the same
  fixed cost.
- We report P10 / median / P90 total cost, so an operator can see
  "in the unlucky 10% of cases, this route could cost you $X" rather than
  a single average that hides the tail risk.
"""

import random

from .scoring import DELAY_COST_CONSTANT


def simulate_route_outcomes(route: dict, n_trials: int = 2000, prob_noise: float = 0.1) -> dict:
    base_p = route["delay_probability"]
    outcomes = []
    delay_count = 0

    for _ in range(n_trials):
        p = min(1.0, max(0.0, base_p + random.uniform(-prob_noise, prob_noise)))
        delay_occurs = random.random() < p
        if delay_occurs:
            delay_count += 1

        total_cost = route["cost_usd"]
        if delay_occurs:
            severity = random.uniform(0.5, 2.0)
            total_cost += DELAY_COST_CONSTANT * severity

        outcomes.append(total_cost)

    outcomes.sort()
    n = len(outcomes)
    return {
        "route_id": route["route_id"],
        "p10_cost": outcomes[int(0.10 * n)],
        "median_cost": outcomes[int(0.50 * n)],
        "p90_cost": outcomes[int(0.90 * n)],
        "pct_trials_with_delay": round(100 * delay_count / n_trials, 1),
        "n_trials": n_trials,
    }