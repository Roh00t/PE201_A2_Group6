#!/usr/bin/env python3
"""
PE6201 · A2 — THE ERROR BAR, REHEARSED OFFLINE  (D4, D5b)
====================================================================
    python3 evals/test_significance.py

Free, offline, no key. Checks the three functions that decide whether a
gap between two battery rows means anything:

    metrics.wilson_interval   the range consistent with k of n
    metrics.two_proportion_p  can two rows be told apart
    metrics.separability      the verdict over the whole table

WHY THESE NEED TESTS AT ALL. They are the only functions in the harness
whose OUTPUT IS AN ARGUMENT rather than a number. A pass rate that is
wrong is visibly wrong. A confidence interval that is wrong looks
exactly like a confidence interval that is right, and it would let us
claim a finding we do not have - which is the failure this whole
assignment is arranged against.

The fixed values below are computed by hand from the Wilson and pooled
z formulas, not copied from our own output, so a regression in the
implementation cannot quietly rewrite the expectation.
====================================================================
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals import metrics                          # noqa: E402

PASSED = FAILED = 0


def check(name, ok):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print("  PASS  %s" % name)
    else:
        FAILED += 1
        print("  FAIL  %s" % name)


def near(a, b, tol=0.002):
    return a is not None and abs(a - b) <= tol


def main():
    print("\n  1 · wilson_interval")
    lo, hi = metrics.wilson_interval(54, 60)
    check("54/60 gives the interval we quote in the report (79.9–95.3%)",
          near(lo, 0.799, 0.003) and near(hi, 0.953, 0.003))
    check("the interval brackets the point estimate", lo < 54 / 60 < hi)

    lo, hi = metrics.wilson_interval(60, 60)
    # THE REASON WE USE WILSON. The textbook normal interval returns
    # (1.0, 1.0) here - zero width - and would let a single clean battery
    # claim certainty. Wilson keeps a lower bound below 1.
    check("60/60 does NOT collapse to a point (why not the normal "
          "approximation)", lo < 1.0 and hi <= 1.0)
    check("60/60 stays inside [0, 1]", 0.0 <= lo and hi <= 1.0)

    lo, hi = metrics.wilson_interval(0, 60)
    check("0/60 stays inside [0, 1]", lo >= 0.0 and hi <= 1.0)
    check("an empty arm returns (None, None)",
          metrics.wilson_interval(0, 0) == (None, None))

    lo60, hi60 = metrics.wilson_interval(48, 60)
    lo600, hi600 = metrics.wilson_interval(480, 600)
    check("ten times the trials narrows the interval",
          (hi600 - lo600) < (hi60 - lo60))

    print("\n  2 · two_proportion_p")
    z, p = metrics.two_proportion_p(54, 60, 48, 60)
    check("Haiku 54/60 vs deepseek 48/60 is NOT significant (p≈0.125)",
          near(p, 0.125, 0.005) and p > 0.05)
    z, p = metrics.two_proportion_p(54, 60, 41, 60)
    check("Haiku 54/60 vs qwen 41/60 IS significant (p≈0.003)",
          p < 0.05 and near(p, 0.003, 0.002))
    z, p = metrics.two_proportion_p(48, 60, 48, 60)
    check("identical rates cannot be separated", p == 1.0 and z == 0.0)
    check("an empty arm is not a comparison",
          metrics.two_proportion_p(5, 0, 5, 10) == (0.0, 1.0))
    za, _ = metrics.two_proportion_p(54, 60, 41, 60)
    zb, _ = metrics.two_proportion_p(41, 60, 54, 60)
    check("the test is symmetric in magnitude", near(za, -zb, 1e-9))

    print("\n  3 · separability over a table")
    rows = [
        {"model": "best", "member": "a", "prompt": "v2", "trials": 60,
         "pass_rate": 54 / 60},
        {"model": "close", "member": "b", "prompt": "v2", "trials": 60,
         "pass_rate": 48 / 60},
        {"model": "far", "member": "c", "prompt": "v2", "trials": 60,
         "pass_rate": 41 / 60},
        {"model": "ignored_v1", "member": "d", "prompt": "v1", "trials": 60,
         "pass_rate": 31 / 60},
    ]
    sep = metrics.separability(rows)
    check("the best v2 row is found", sep["best"]["model"] == "best")
    check("the v1 pass is excluded - it is a different prompt, not a rival",
          all(r["model"] != "ignored_v1" for r in sep["rivals"]))
    byname = {r["model"]: r for r in sep["rivals"]}
    check("the close rival is reported INSIDE the noise",
          byname["close"]["separated"] is False)
    check("the distant rival is reported as separated",
          byname["far"]["separated"] is True)
    check("fewer than two live rows is not a comparison",
          metrics.separability(rows[:1]) is None)

    print("\n  4 · the table actually carries it")
    md = os.path.join(ROOT, "results", "live", "battery_table.md")
    if os.path.exists(md):
        text = open(md, encoding="utf-8").read()
        check("battery_table.md has a 95% CI column", "95% CI" in text)
        check("battery_table.md states the negative result",
              "INSIDE THE NOISE" in text)
    else:
        check("battery_table.md exists", False)

    print("\n" + "=" * 62)
    print("  %d passed, %d failed" % (PASSED, FAILED))
    if not FAILED:
        print("  A gap that survives this is a finding. One that does not")
        print("  is a sample size.")
    print("=" * 62 + "\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
