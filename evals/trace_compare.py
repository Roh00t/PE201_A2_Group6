#!/usr/bin/env python3
"""
PE6201 · A2 — THE SAME CASE, ACROSS EVERY MODEL  (D5b, and the demo)
====================================================================
    python3 evals/trace_compare.py --case CLM-8842
    python3 evals/trace_compare.py --case CLM-8925 --trial 2
    python3 evals/trace_compare.py --worst          # pick the case that
                                                    # separated the models

Free. Reads the committed battery files under results/live/ and prints,
for one case, what each model actually did turn by turn.

WHY THIS EXISTS. The D5(b) table gives one pass rate per model, and a
pass rate cannot show WHERE two models diverged - only that they did.
The brief asks for exactly that divergence: "not which model is best in
the abstract, but which model does your job at what cost, and where they
diverge. Expect them to diverge most on the negative cases; that is the
finding to look for."

This is also the one artefact that puts "the thought process of each
model" on screen for the demonstration, which the marking scheme reads
under Communication.

WHAT IT CANNOT SHOW. The tool ARGUMENTS and the model's per-turn thought
are not kept in the results file - only the ordered tool names, the
decision and the counters. `python3 run_eval.py <case>` shows a full
turn-by-turn trace with arguments, but only for the scripted backend.
Stated here rather than implied.
====================================================================
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals import harness                               # noqa: E402
from evals import metrics                               # noqa: E402

LIVE_DIR = os.path.join(ROOT, "results", "live")


def load_runs():
    runs = []
    for path in sorted(glob.glob(os.path.join(LIVE_DIR, "battery__*.json"))):
        with open(path, encoding="utf-8") as fh:
            runs.append(json.load(fh))
    return runs


def worst_case(runs, key):
    """The case with the widest spread of outcomes across models.

    That is the interesting one: a case every model gets right teaches
    nothing, and so does one every model gets wrong.
    """
    spread = {}
    for run in runs:
        for r in run.get("results", []):
            if r.get("trial") != 1:
                continue
            spread.setdefault(r["case_id"], set()).add(
                (r.get("record") or {}).get("decision"))
    if not spread:
        return None
    return max(spread.items(), key=lambda kv: len(kv[1]))[0]


def render(runs, case_id, trial, key):
    exp = key.get(case_id) or {}
    out = []
    w = out.append

    w("=" * 76)
    w("  %s   trial %d" % (case_id, trial))
    w("=" * 76)
    w("  EXPECTED   decision %s" % exp.get("expected_decision"))
    if exp.get("trigger"):
        w("             trigger  %s" % exp["trigger"])
    if exp.get("missing"):
        w("             missing  %s" % exp["missing"])
    w("  family     %s%s" % (exp.get("family", "?"),
                             "   NEGATIVE CASE" if harness.is_negative(exp)
                             else ""))
    if exp.get("note"):
        w("  note       %s" % exp["note"][:70])
    w("")

    for run in runs:
        t = metrics.trace(run.get("results", []), case_id, trial)
        if not t:
            continue
        w("-" * 76)
        w("  %-14s %s   [prompt %s]"
          % (run.get("member", "?"), run.get("model") or run.get("backend"),
             run.get("prompt_version", "?")))
        w("-" * 76)
        w("    %s in %s turn(s), %d tool call(s), US$%.5f"
          % ("PASS" if t["passed"] else "FAIL", t["turns"],
             len(t["tools_called"]), t["cost_usd"] or 0.0))

        # The ordered call list is the closest thing we keep to the
        # model's reasoning. Grouping is not recoverable from the record,
        # so they are printed in order rather than invented into turns.
        w("    tools:  %s" % (" -> ".join(t["tools_called"])
                              if t["tools_called"] else "(none called)"))
        w("    said:   %s" % (t["decision"] or "?")
          + ("  [trigger %s]" % t["trigger"] if t.get("trigger") else "")
          + ("  [missing %s]" % str(t["missing"])[:34] if t.get("missing") else ""))
        if t["stopped_by"]:
            w("    STOPPED BY OUR CODE: %s   <- not a decision the model made"
              % t["stopped_by"])
        if t["reason"]:
            w("    reason: %s" % t["reason"][:66])
        for f in t["fails"][:2]:
            w("    why:    %s" % str(f)[:66])
        w("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trace_compare.py")
    ap.add_argument("--case", help="e.g. CLM-8842")
    ap.add_argument("--trial", type=int, default=1)
    ap.add_argument("--worst", action="store_true",
                    help="pick the case the models disagreed on most")
    args = ap.parse_args(argv)

    runs = load_runs()
    if not runs:
        print("\n  No battery results in results/live/ yet.\n"
              "  Run:  python3 run_live_battery.py --name \"<you>\"\n")
        return 1

    rows = harness.load_key()
    key = ({r["case_id"]: r for r in rows} if isinstance(rows, list) else rows)

    case = args.case or (worst_case(runs, key) if args.worst else None)
    if not case:
        print("\n  Give --case CLM-xxxx, or --worst to pick the most "
              "divisive one.\n")
        return 2
    if case not in key:
        print("\n  %r is not in the answer key.\n" % case)
        return 2

    print()
    print(render(runs, case, args.trial, key))
    if len(runs) == 1:
        print("  Only ONE battery has been run, so there is nothing to")
        print("  compare against yet. This becomes a comparison once the")
        print("  other members have run.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
