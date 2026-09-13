#!/usr/bin/env python3
"""
PE6201 · A2 — WHAT THE BATTERY ACTUALLY MEASURED  (D4, D5b, D6, D7)
====================================================================
    python3 evals/metrics.py results/live/battery__<member>__*.json

Free. Pure functions over a results file already on disk. No network, no
key, no tokens. Read by evals/aggregate_battery.py and by the demo.

--------------------------------------------------------------------
THE RULE THIS WHOLE MODULE RESTS ON

Split the trials into THREE POPULATIONS before computing anything:

    completed     the model produced a decision        stopped_by is None
    halted        our code stopped it first            stopped_by is set
    unparseable   the reply was not usable             a parse failure

and compute the confusion matrix over the COMPLETED ones only.

WHY THIS IS NOT PEDANTRY. On rohit_panda's 2026-09-13 run, 48 of 60
trials were killed on turn 2 by our own de-duplication guard, and the
loop recorded each halt as `decision: escalate`. Count those naively and
the matrix reports the model escalating 56 of 60 times. It actually
CHOSE to escalate 8 times. Every precision and recall figure built on
the raw `decision` field inherits that error, looks entirely reasonable,
and is wrong by a factor of seven.

A metric that cannot tell "the model decided X" from "our code stopped it
before it decided" is not measuring the model.

--------------------------------------------------------------------
AND THE SECOND RULE: every rate carries its denominator. No percentage
is returned or printed without the fraction it came from, because a
pass rate without a trial count is not a measurement. [brief D4]
====================================================================
"""
import collections
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals import harness                                   # noqa: E402

OUTCOMES = ("approve_in_principle", "request_document", "escalate")
UNPARSEABLE = "did not return parseable JSON"

# The scripted agent calls seven tools on a full approval. A live model
# calling two has not done the work, whatever it then decided.
SCRIPTED_TOOLS_PER_RUN = 7


# =====================================================================
# THE SPLIT
# =====================================================================
def split(results):
    """Three populations, and they must sum to the trial count."""
    completed, halted, unparseable = [], [], []
    for r in results:
        rec = r.get("record") or {}
        reason = str(rec.get("reason") or "")
        if UNPARSEABLE in reason:
            unparseable.append(r)
        elif rec.get("stopped_by"):
            halted.append(r)
        else:
            completed.append(r)
    return {"completed": completed, "halted": halted,
            "unparseable": unparseable, "total": len(results)}


def frac(n, d):
    """A fraction that never pretends to be a rate it cannot support."""
    return {"n": n, "d": d,
            "rate": (float(n) / d) if d else None,
            "text": ("%d/%d (%.1f%%)" % (n, d, 100.0 * n / d)) if d
                    else "%d/0 (n/a)" % n}


# =====================================================================
# 1 · OUTCOME QUALITY — completed trials only
# =====================================================================
def outcome_quality(results, key=None):
    """3x3 confusion matrix with per-class precision, recall and F1.

    COMPLETED TRIALS ONLY. See the module docstring for why; this is the
    single decision that separates a real measurement from a plausible
    one.
    """
    key = key or _key_map(results)
    pops = split(results)
    rows = pops["completed"]

    matrix = {w: {g: 0 for g in OUTCOMES} for w in OUTCOMES}
    for r in rows:
        want = (key.get(r["case_id"]) or {}).get("expected_decision")
        got = (r.get("record") or {}).get("decision")
        if want in OUTCOMES and got in OUTCOMES:
            matrix[want][got] += 1

    per_class, f1s = {}, []
    for c in OUTCOMES:
        tp = matrix[c][c]
        fp = sum(matrix[w][c] for w in OUTCOMES if w != c)
        fn = sum(matrix[c][g] for g in OUTCOMES if g != c)
        prec = frac(tp, tp + fp)
        rec = frac(tp, tp + fn)
        p, rr = prec["rate"], rec["rate"]
        f1 = (2 * p * rr / (p + rr)) if (p and rr) else (0.0 if (p is not None
                                                                and rr is not None)
                                                        else None)
        per_class[c] = {"support": tp + fn, "precision": prec,
                        "recall": rec, "f1": f1}
        if f1 is not None:
            f1s.append(f1)

    return {
        "populations": {k: len(v) for k, v in pops.items() if k != "total"},
        "total_trials": pops["total"],
        "graded_here": len(rows),
        "matrix": matrix,
        "per_class": per_class,
        "macro_f1": (sum(f1s) / len(f1s)) if f1s else None,
        "accuracy_of_completed": frac(
            sum(matrix[c][c] for c in OUTCOMES), len(rows)),
    }


# =====================================================================
# 2 · RUN SHAPE AND EFFICIENCY
# =====================================================================
def run_shape(results):
    """How the runs were shaped, and what a CORRECT answer cost.

    `cost_per_passed_trial` is the number D6 layer 1 wants. Cost per
    trial flatters a model that fails cheaply: on the 2026-09-13 run the
    two differ by 60x, and only one of them is the cost of getting the
    job done.
    """
    recs = [(r.get("record") or {}) for r in results]
    turns = [rec.get("turns") or 0 for rec in recs]
    tools = [len(rec.get("evidence") or []) for rec in recs]
    cost = sum(float(rec.get("cost_usd") or 0) for rec in recs)
    passed = sum(1 for r in results if r.get("passed"))

    return {
        "turns": {
            "distribution": dict(sorted(collections.Counter(turns).items())),
            "median": statistics.median(turns) if turns else None,
            "max": max(turns) if turns else None,
            "zero_turn": sum(1 for t in turns if t == 0),
        },
        "tools_per_run": {
            "mean": (sum(tools) / len(tools)) if tools else None,
            "scripted_baseline": SCRIPTED_TOOLS_PER_RUN,
        },
        "tokens_in": sum(int(rec.get("tokens_in") or 0) for rec in recs),
        "tokens_out": sum(int(rec.get("tokens_out") or 0) for rec in recs),
        "cost_usd": cost,
        "cost_per_trial": (cost / len(recs)) if recs else None,
        # None, never 0 - a run that passed nothing has no cost per
        # success, and printing 0.0 there would read as "free and
        # correct" rather than "never correct".
        "cost_per_passed_trial": (cost / passed) if passed else None,
        "passed": frac(passed, len(results)),
    }


# =====================================================================
# 3 · FAILURE TAXONOMY — and which layer owns each bucket
# =====================================================================
# Keyed off the `fails` strings harness.code_check already produces. We
# do NOT re-grade here: a second implementation of the same comparison
# is a second answer to the same question.
LAYER = {
    "halted_by_guardrail": "loop control",
    "output_truncated": "tool interface (token cap)",
    "unparseable": "tool interface (output contract)",
    "wrong_decision": "model",
    "right_decision_wrong_trigger": "model / prompt",
    "right_decision_wrong_missing": "prompt",
    "other": "unclassified",
}


def failure_taxonomy(results, key=None):
    """Every FAILED trial bucketed by cause, with the layer that owns it."""
    key = key or _key_map(results)
    buckets = collections.Counter()
    examples = {}

    for r in results:
        if r.get("passed"):
            continue
        rec = r.get("record") or {}
        reason = str(rec.get("reason") or "")
        stopped = rec.get("stopped_by")
        fails = [str(f) for f in (r.get("fails") or [])]

        if UNPARSEABLE in reason:
            b = "unparseable"
        elif stopped == "output_truncated":
            b = "output_truncated"
        elif stopped:
            b = "halted_by_guardrail"
        elif any(f.startswith("decision ") for f in fails):
            b = "wrong_decision"
        elif any(f.startswith("trigger ") for f in fails):
            b = "right_decision_wrong_trigger"
        elif any(f.startswith("missing ") for f in fails):
            b = "right_decision_wrong_missing"
        else:
            b = "other"

        buckets[b] += 1
        examples.setdefault(b, "%s: %s" % (
            r.get("case_id"),
            (fails[0] if fails else reason)[:72]))

    # Halts are worth naming individually - "duplicate_action x48" is a
    # different engineering problem from "step_cap x48".
    by_guard = collections.Counter(
        (r.get("record") or {}).get("stopped_by")
        for r in results
        if not r.get("passed") and (r.get("record") or {}).get("stopped_by"))

    return {
        "failed": sum(buckets.values()),
        "buckets": [{"cause": b, "count": n, "layer": LAYER.get(b, "?"),
                     "example": examples.get(b, "")}
                    for b, n in buckets.most_common()],
        "halts_by_guardrail": dict(by_guard),
    }


# =====================================================================
# 4 · TRACE — one case, turn by turn, for the demo
# =====================================================================
def trace(results, case_id, trial=1):
    """What the agent actually did on one case, in order."""
    for r in results:
        if r.get("case_id") == case_id and r.get("trial") == trial:
            rec = r.get("record") or {}
            return {
                "case_id": case_id, "trial": trial,
                "passed": r.get("passed"),
                "turns": rec.get("turns"),
                "tools_called": list(rec.get("evidence") or []),
                "per_turn_tokens": rec.get("turn_tokens") or [],
                "decision": rec.get("decision"),
                "trigger": rec.get("trigger"),
                "missing": rec.get("missing"),
                "reason": rec.get("reason"),
                "stopped_by": rec.get("stopped_by"),
                "guardrails_fired": rec.get("guardrails_fired") or [],
                "fails": r.get("fails") or [],
                "cost_usd": rec.get("cost_usd"),
            }
    return None


# =====================================================================
# HELPERS
# =====================================================================
def _key_map(results=None, problem=None):
    rows = harness.load_key(problem)
    return ({r["case_id"]: r for r in rows} if isinstance(rows, list)
            else rows)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# =====================================================================
# RENDERING
# =====================================================================
def render(doc, key=None):
    results = doc.get("results") or []
    key = key or _key_map()
    oq = outcome_quality(results, key)
    rs = run_shape(results)
    ft = failure_taxonomy(results, key)
    out = []
    w = out.append

    w("=" * 74)
    w("  %s · %s · prompt %s · %s"
      % (doc.get("member", "?"), doc.get("model") or doc.get("backend"),
         doc.get("prompt_version", "?"), doc.get("date", "?")))
    w("=" * 74)

    p = oq["populations"]
    w("")
    w("  WHAT HAPPENED TO %d TRIALS" % oq["total_trials"])
    w("    completed (the model decided)     %d" % p["completed"])
    w("    halted by our own code            %d" % p["halted"])
    w("    unparseable output                %d" % p["unparseable"])
    if p["halted"] or p["unparseable"]:
        w("    ^ only the first row can be scored as a model decision.")
        w("      Counting the others as predictions would report the model")
        w("      choosing an outcome it was never allowed to reach.")

    w("")
    w("  CONFUSION MATRIX - completed trials only (%d)" % oq["graded_here"])
    w("    %-24s %s" % ("", "  ".join("%-10s" % g[:10] for g in OUTCOMES)))
    for want in OUTCOMES:
        w("    want %-19s %s"
          % (want[:19], "  ".join("%-10d" % oq["matrix"][want][g]
                                  for g in OUTCOMES)))
    w("")
    w("    %-24s %-12s %-12s %s" % ("class", "precision", "recall", "F1"))
    for c in OUTCOMES:
        pc = oq["per_class"][c]
        w("    %-24s %-12s %-12s %s"
          % (c[:24], pc["precision"]["text"], pc["recall"]["text"],
             "%.2f" % pc["f1"] if pc["f1"] is not None else "n/a"))
    w("    %-24s macro-F1 %s   accuracy %s"
      % ("", "%.2f" % oq["macro_f1"] if oq["macro_f1"] is not None else "n/a",
         oq["accuracy_of_completed"]["text"]))

    w("")
    w("  RUN SHAPE")
    w("    turns            %s   median %s  max %s"
      % (rs["turns"]["distribution"], rs["turns"]["median"], rs["turns"]["max"]))
    w("    tools per run    %.1f   (scripted does %d on a full approval)"
      % (rs["tools_per_run"]["mean"] or 0, SCRIPTED_TOOLS_PER_RUN))
    w("    tokens           %s in / %s out"
      % ("{:,}".format(rs["tokens_in"]), "{:,}".format(rs["tokens_out"])))
    w("    cost per trial          US$%.5f" % (rs["cost_per_trial"] or 0))
    w("    cost per PASSED trial   %s"
      % ("US$%.5f" % rs["cost_per_passed_trial"]
         if rs["cost_per_passed_trial"] is not None
         else "n/a - nothing passed"))
    w("    ^ the second is the one D6 layer 1 wants. A model that fails")
    w("      cheaply looks cheap only on the first.")

    w("")
    w("  WHY %d TRIALS FAILED" % ft["failed"])
    w("    %-32s %-6s %s" % ("cause", "count", "layer the fix belongs in"))
    for b in ft["buckets"]:
        w("    %-32s %-6d %s" % (b["cause"], b["count"], b["layer"]))
    if ft["halts_by_guardrail"]:
        w("    halts by guardrail: %s" % ft["halts_by_guardrail"])
    for b in ft["buckets"][:3]:
        if b["example"]:
            w("      e.g. %s" % b["example"])
    w("")
    return "\n".join(out)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    for path in argv:
        print(render(load(path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
