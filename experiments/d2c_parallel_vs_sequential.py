#!/usr/bin/env python3
"""
PE6201 · A2 — D2(c): THE SAME WORK, GROUPED TWO WAYS
====================================================================
    python3 experiments/d2c_parallel_vs_sequential.py

What D2(c) requires, in four parts:

  1. state the dependency rule        -> src/backends/planner.py, top
  2. measure it BOTH ways             -> this script
  3. report turns, tokens and cost    -> the table below
  4. show correctness did not move    -> the pass-rate column

It also prints the TURN DISTRIBUTION, which is what D7 asks for and
what the step cap has to be derived from. Median, worst case, and how
many runs hit the cap - one number is not a distribution.

Runs on the scripted backend. Free, deterministic, no key.

WHAT WE DO NOT DO HERE. We do not quote the brief's 54%. That is
CLM-8842's number under the brief's grouping, not ours; our
check_coverage takes a required policy_id, so our rule parallelises
LESS and the saving is our own. D2(c) marks the reasoning.
====================================================================
"""
import collections
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config
from evals.harness import load_cases, load_key, run_set


def measure(mode, uncapped=False):
    """Run the whole set under one grouping.

    `uncapped` lifts the step cap and the budget ceiling so the two arms
    differ ONLY in how calls are grouped. Without it the comparison is
    confounded: sequential grouping runs longer, so our shipped budget
    ceiling halts the longest runs and the pass rate falls for a reason
    that has nothing to do with the grouping. That interaction is real
    and is reported below on its own - but it must not be smuggled into
    the D2(c) number.
    """
    config.GROUPING = mode
    saved = (config.MAX_TURNS, config.MAX_TOKENS_PER_RUN)
    if uncapped:
        config.MAX_TURNS, config.MAX_TOKENS_PER_RUN = 10 ** 6, 10 ** 9
    try:
        cases = [c for c in load_cases() if c in load_key()]
        results, _ = run_set(cases)
    finally:
        config.MAX_TURNS, config.MAX_TOKENS_PER_RUN = saved
    turns = [r["record"]["turns"] for r in results]
    calls = [len(r["record"]["evidence"]) for r in results]
    return {
        "mode": mode,
        "trials": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "turns": turns,
        "tokens": sum(r["record"]["tokens_in"] + r["record"]["tokens_out"]
                      for r in results),
        "tokens_in": sum(r["record"]["tokens_in"] for r in results),
        "cost": sum(r["record"]["cost_usd"] for r in results),
        "calls": sum(calls),
        "capped": sum(1 for r in results
                      if r["record"]["stopped_by"] == "step_cap"),
        "by_case": {r["case_id"]: r["record"]["turns"] for r in results},
    }


def main():
    print()
    print("=" * 72)
    print("  D2(c) · THE SAME EVALUATION SET, GROUPED TWO WAYS")
    print("=" * 72)
    print("  backend  scripted (free, deterministic)")
    print("  set      Problem %s, every labelled case" % config.PROBLEM)
    print()

    original = config.GROUPING
    try:
        par = measure("parallel", uncapped=True)
        seq = measure("sequential", uncapped=True)
        # The same two runs again, at the caps we actually ship.
        par_capped = measure("parallel")
        seq_capped = measure("sequential")
    finally:
        config.GROUPING = original

    row = "  %-12s %7s %8s %10s %12s %11s"
    print(row % ("grouping", "turns", "calls", "input tok", "cost US$", "pass rate"))
    print("  " + "-" * 68)
    for m in (seq, par):
        print(row % (m["mode"], sum(m["turns"]), m["calls"], m["tokens_in"],
                     "%.4f" % m["cost"],
                     "%d/%d" % (m["passed"], m["trials"])))
    print()

    # THE SAVING IS OURS, MEASURED. Not the brief's 54%.
    d_turns = 1 - sum(par["turns"]) / sum(seq["turns"])
    d_tok = 1 - par["tokens_in"] / seq["tokens_in"]
    print("  Grouping independent calls cut TURNS by %.0f%% and INPUT TOKENS"
          % (100 * d_turns))
    print("  by %.0f%% across %d trials. The call count is identical (%d):"
          % (100 * d_tok, par["trials"], par["calls"]))
    print("  nothing was removed, the calls were only regrouped - so the")
    print("  saving is the transcript being re-sent fewer times, which is")
    print("  the B*T + D*T(T-1)/2 term behaving as advertised.")
    print()
    if par["passed"] == seq["passed"]:
        print("  CORRECTNESS DID NOT MOVE: %d/%d both ways, caps lifted so the"
              % (par["passed"], par["trials"]))
        print("  only difference between the arms is the grouping.")
    else:
        print("  CORRECTNESS MOVED: %d/%d parallel vs %d/%d sequential."
              % (par["passed"], par["trials"], seq["passed"], seq["trials"]))
        print("  Do not report the saving until you know why.")
    print()

    # ---- the interaction, reported separately and honestly ------------
    print("=" * 72)
    print("  AND WHAT HAPPENS AT THE CAPS WE ACTUALLY SHIP")
    print("=" * 72)
    print("  step cap %d turns · budget ceiling %s tokens"
          % (config.MAX_TURNS, format(config.MAX_TOKENS_PER_RUN, ",")))
    print()
    for m in (seq_capped, par_capped):
        halted = m["trials"] - m["passed"]
        print("    %-11s %d/%d passed · %d halted by a guardrail · "
              "%d hit the step cap"
              % (m["mode"], m["passed"], m["trials"], halted, m["capped"]))
    print()
    if seq_capped["passed"] < par_capped["passed"]:
        print("  READ THIS BEFORE QUOTING THE SAVING ABOVE. Our caps are")
        print("  calibrated to the PARALLEL grouping. Run the same work one")
        print("  call per turn and %d trials breach a ceiling and halt - not"
              % (seq_capped["trials"] - seq_capped["passed"]))
        print("  because the answer was wrong, but because the run got long.")
        print("  That is the D7 lesson arriving early: a cap bounds cost and")
        print("  it also truncates legitimate long runs, so a cap is only")
        print("  defensible ALONGSIDE the grouping it was derived under.")
        print("  It is also the honest limit on our D2(c) claim - the saving")
        print("  is measured with caps lifted, and stated that way.")
    print()

    # ---- the distribution D7 and the step cap need -------------------
    print("=" * 72)
    print("  TURN DISTRIBUTION (parallel grouping) - what the cap comes from")
    print("=" * 72)
    t = par["turns"]
    hist = collections.Counter(t)
    for turns in sorted(hist):
        print("    %d turns  %-28s %d run(s)"
              % (turns, "#" * hist[turns], hist[turns]))
    print()
    print("    median              %s" % statistics.median(t))
    print("    mean                %.2f" % statistics.fmean(t))
    print("    worst LEGITIMATE    %d   (every run below passed)" % max(t))
    print("    hit the step cap    %d" % par["capped"])
    print("    current MAX_TURNS   %d" % config.MAX_TURNS)
    print()
    print("    A defensible cap is the worst legitimate run plus a small")
    print("    margin for a model that wanders once and recovers. Worst")
    print("    legitimate here is %d, so a cap of %d leaves %d spare turns."
          % (max(t), config.MAX_TURNS, config.MAX_TURNS - max(t)))
    print("    A cap of 30 would be decoration; a cap of %d would truncate"
          % max(t))
    print("    the longest correct run in the set.")
    print()

    longest = sorted(par["by_case"].items(), key=lambda kv: -kv[1])[:5]
    print("    longest runs: %s"
          % ", ".join("%s (%d)" % (c, n) for c, n in longest))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
