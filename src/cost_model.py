#!/usr/bin/env python3
"""D6 three-layer cost model. Standard-library only.

The program deliberately refuses null inputs. That prevents an illustrative
price or an ungraded scripted pass rate from silently becoming a submitted
business claim.
"""
import argparse
import json
import math
import os
import sys


def _number(value, path):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a measured or sourced number, not %r" % (path, value))
    if not math.isfinite(value) or value < 0:
        raise ValueError("%s must be finite and non-negative" % path)
    return float(value)


def model_cost(name, row, failure_cost):
    cost_tasks = _number(row.get("cost_task_count", row.get("trials")),
                         "%s.cost_task_count" % name)
    success_total = _number(row.get("success_total"), "%s.success_total" % name)
    success_passed = _number(row.get("success_passed"), "%s.success_passed" % name)
    if cost_tasks <= 0 or success_total <= 0:
        raise ValueError("%s cost_task_count and success_total must be above zero" % name)
    if success_passed > success_total:
        raise ValueError("%s success_passed cannot exceed success_total" % name)

    tokens_in = _number(row.get("tokens_in"), "%s.tokens_in" % name)
    tokens_out = _number(row.get("tokens_out"), "%s.tokens_out" % name)
    price_in = _number(row.get("price_in_per_million"),
                       "%s.price_in_per_million" % name)
    price_out = _number(row.get("price_out_per_million"),
                        "%s.price_out_per_million" % name)
    tool_total = _number(row.get("tool_fees_total"), "%s.tool_fees_total" % name)
    retrieval_total = _number(row.get("retrieval_fees_total"),
                              "%s.retrieval_fees_total" % name)

    p = success_passed / success_total
    token_cost = ((tokens_in / cost_tasks) * price_in
                  + (tokens_out / cost_tasks) * price_out) / 1_000_000
    layer1 = token_cost + (tool_total + retrieval_total) / cost_tasks
    layer2 = (1 - p) * failure_cost
    return {
        "success_rate": p,
        "cost_task_count": cost_tasks,
        "average_tokens_in": tokens_in / cost_tasks,
        "average_tokens_out": tokens_out / cost_tasks,
        "layer1_variable_usd_per_task": layer1,
        "layer2_expected_failure_usd_per_task": layer2,
        "expected_usd_per_task_before_fixed": layer1 + layer2,
    }


def calculate(doc):
    volume = _number(doc.get("monthly_volume"), "monthly_volume")
    failure_cost = _number(doc.get("failure_cost_usd"), "failure_cost_usd")
    fixed_rows = doc.get("fixed_monthly_usd") or {}
    required_fixed = ("monitoring", "storage_infrastructure", "evaluation", "maintenance")
    missing = [key for key in required_fixed if key not in fixed_rows]
    if missing:
        raise ValueError("fixed_monthly_usd is missing: %s" % ", ".join(missing))
    fixed = {key: _number(fixed_rows[key], "fixed_monthly_usd.%s" % key)
             for key in required_fixed}
    layer3 = sum(fixed.values())

    models = {name: model_cost(name, row, failure_cost)
              for name, row in (doc.get("models") or {}).items()}
    if not models:
        raise ValueError("models must contain at least one measured run")
    deployed_name = doc.get("deployed_model")
    if deployed_name not in models:
        raise ValueError("deployed_model must name one entry in models")
    deployed = models[deployed_name]

    cap_rows = doc.get("caps") or {}
    required_caps = ("step_cap", "budget_ceiling_tokens_per_run",
                     "monthly_limit_per_user")
    missing_caps = [key for key in required_caps if key not in cap_rows]
    if missing_caps:
        raise ValueError("caps is missing: %s" % ", ".join(missing_caps))
    caps = {key: _number(cap_rows[key], "caps.%s" % key)
            for key in required_caps}

    sensitivities = {}
    for delta in (-0.10, 0.0, 0.10):
        p = min(1.0, max(0.0, deployed["success_rate"] + delta))
        layer2 = (1 - p) * failure_cost
        sensitivities["%+.0fpp" % (delta * 100)] = {
            "success_rate": p,
            "monthly_usd": ((deployed["layer1_variable_usd_per_task"] + layer2)
                            * volume + layer3),
        }

    result = {
        "monthly_volume": volume,
        "failure_cost_usd": failure_cost,
        "layer3_fixed_monthly_usd": layer3,
        "layer3_breakdown_usd": fixed,
        "models": models,
        "deployed_model": deployed_name,
        "deployed_expected_monthly_usd": (
            deployed["expected_usd_per_task_before_fixed"] * volume + layer3),
        "success_rate_sensitivity": sensitivities,
        "caps": caps,
    }

    cheap_name, expensive_name = doc.get("cheap_model"), doc.get("expensive_model")
    if cheap_name or expensive_name:
        if cheap_name not in models or expensive_name not in models:
            raise ValueError("cheap_model and expensive_model must name entries in models")
        cheap = models[cheap_name]
        expensive = models[expensive_name]
        c = cheap["layer1_variable_usd_per_task"]
        e = expensive["expected_usd_per_task_before_fixed"]
        raw = 1 - (e - c) / failure_cost
        result["cheap_model_break_even"] = {
            "cheap_model": cheap_name,
            "expensive_model": expensive_name,
            "formula": "1 - (E - C) / F",
            "C_cheap_variable_cost_usd": c,
            "E_expensive_all_in_before_fixed_usd": e,
            "F_failure_cost_usd": failure_cost,
            "required_cheap_success_rate_raw": raw,
            "required_cheap_success_rate_feasible_range": min(1.0, max(0.0, raw)),
        }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="completed D6 JSON input")
    parser.add_argument("--out", help="write the result JSON here")
    args = parser.parse_args(argv)
    with open(args.input, encoding="utf-8") as fh:
        doc = json.load(fh)
    try:
        result = calculate(doc)
    except ValueError as exc:
        print("D6 input is incomplete: %s" % exc, file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rendered + "\n")
        print("Wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
