#!/usr/bin/env python3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from cost_model import calculate


doc = {
    "monthly_volume": 8000,
    "failure_cost_usd": 7.6,
    "deployed_model": "cheap",
    "cheap_model": "cheap",
    "expensive_model": "expensive",
    "models": {
        "cheap": {"cost_task_count": 100, "success_passed": 90, "success_total": 100,
                  "tokens_in": 1_000_000, "tokens_out": 100_000,
                  "price_in_per_million": 1, "price_out_per_million": 2,
                  "tool_fees_total": 0, "retrieval_fees_total": 0},
        "expensive": {"cost_task_count": 100, "success_passed": 98, "success_total": 100,
                      "tokens_in": 1_000_000, "tokens_out": 100_000,
                      "price_in_per_million": 5, "price_out_per_million": 10,
                      "tool_fees_total": 0, "retrieval_fees_total": 0},
    },
    "fixed_monthly_usd": {"monitoring": 10, "storage_infrastructure": 20,
                          "evaluation": 30, "maintenance": 40},
    "caps": {"step_cap": 8, "budget_ceiling_tokens_per_run": 60000,
             "monthly_limit_per_user": 100},
}

out = calculate(doc)
assert abs(out["models"]["cheap"]["layer1_variable_usd_per_task"] - 0.012) < 1e-12
assert abs(out["models"]["cheap"]["layer2_expected_failure_usd_per_task"] - 0.76) < 1e-12
assert abs(out["deployed_expected_monthly_usd"] - 6276) < 1e-9
assert out["success_rate_sensitivity"]["+10pp"]["success_rate"] == 1.0
print("cost model: 4 checks passed")
