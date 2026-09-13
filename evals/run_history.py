#!/usr/bin/env python3
"""
PE6201 · A2 — EVERY BATTERY, IN ORDER, AND THE BEST RUN PER MODEL  (D5b, D7)
====================================================================
    python3 evals/run_history.py            # print the history
    python3 evals/run_history.py --write    # also write results/history/

Free. Reads every battery file already committed - the live ones AND the
archived ones - and lays them out as a progression. That progression is a
finding in its own right: rohit_panda's model went 0/60 -> 1/60 -> a
five-case gate before any change to the model, and every step was a
defect in our harness, not in the model under test.

WHAT "BEST RUN PER MODEL" MEANS. Highest pass rate; ties go to the lower
ghost-loop rate, then the lower cost per passed trial. Archived runs are
listed in the history but EXCLUDED from "best": they were measured on a
harness that has since been fixed, so they are evidence about the harness,
not about the model.
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

from evals import metrics                                   # noqa: E402

LIVE = os.path.join(ROOT, "results", "live", "battery__*.json")
ARCHIVE = os.path.join(ROOT, "results", "archive", "live", "battery__*.json")
OUT_DIR = os.path.join(ROOT, "results", "history")


def collect():
    rows = []
    for pattern, archived in ((ARCHIVE, True), (LIVE, False)):
        for path in sorted(glob.glob(pattern)):
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
            h = metrics.headline(doc)
            h["archived"] = archived
            h["file"] = os.path.relpath(path, ROOT)
            h["started"] = doc.get("started")
            rows.append(h)
    # Chronological by the run's own start time, then run_id, so the order
    # never depends on the filesystem.
    rows.sort(key=lambda r: (r.get("started") or r.get("date") or "",
                             r.get("run_id") or ""))
    return rows


def _sort_key(r):
    rate = r["passed"]["rate"]
    ghost = r["ghost_loops"]["rate"]["rate"]
    cpp = r["cost_per_passed_trial"]
    return (-(rate if rate is not None else -1),
            ghost if ghost is not None else 1,
            cpp if cpp is not None else float("inf"))


def best_per_model(rows):
    best = {}
    for r in rows:
        if r["archived"]:
            continue
        m = r["model"]
        if m not in best or _sort_key(r) < _sort_key(best[m]):
            best[m] = r
    return best


def _cpp(r):
    return ("US$%.5f" % r["cost_per_passed_trial"]
            if r["cost_per_passed_trial"] is not None else "n/a")


def render(rows):
    out = []
    w = out.append
    w("=" * 110)
    w("  BATTERY HISTORY - %d run(s), oldest first" % len(rows))
    w("=" * 110)
    w("  %-10s %-13s %-34s %-3s %-7s %-15s %-8s %-6s %-12s %s"
      % ("date", "member", "model", "ver", "trials", "passed", "ghost", "turns",
         "US$/pass", "note"))
    w("  " + "-" * 108)
    for r in rows:
        p = r["populations"]
        w("  %-10s %-13s %-34s %-3s %-7s %-15s %-8s %-6s %-12s %s"
          % (r["date"] or "?", (r["member"] or "?")[:13], (r["model"] or "?")[:34],
             r["prompt_version"] or "?", r["trials"], r["passed"]["text"],
             "%.0f%%" % (100 * (r["ghost_loops"]["rate"]["rate"] or 0)),
             r["median_turns"], _cpp(r),
             ("ARCHIVED · " if r["archived"] else "")
             + "%d done/%d halt/%d unp" % (p["completed"], p["halted"], p["unparseable"])))
    w("")
    best = best_per_model(rows)
    w("  BEST RUN PER MODEL - current harness only; archived runs measured a defect")
    w("  " + "-" * 108)
    if not best:
        w("  (no current-harness battery yet)")
    for model in sorted(best):
        r = best[model]
        w("  %-40s %-15s ghost %-5s median %-4s %s   %s"
          % (model, r["passed"]["text"],
             "%.0f%%" % (100 * (r["ghost_loops"]["rate"]["rate"] or 0)),
             r["median_turns"], _cpp(r), r["member"]))
    w("")
    return "\n".join(out)


def write(rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    hist = os.path.join(OUT_DIR, "run_history.jsonl")
    best = os.path.join(OUT_DIR, "best_run_per_model.json")
    with open(hist, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False,
                                default=str) + "\n")
    with open(best, "w", encoding="utf-8") as fh:
        json.dump(best_per_model(rows), fh, indent=2, sort_keys=True,
                  ensure_ascii=False, default=str)
        fh.write("\n")
    return hist, best


def main(argv=None):
    ap = argparse.ArgumentParser(prog="run_history.py")
    ap.add_argument("--write", action="store_true",
                    help="write results/history/run_history.jsonl and "
                         "best_run_per_model.json")
    args = ap.parse_args(argv)
    rows = collect()
    print()
    print(render(rows))
    if args.write:
        for path in write(rows):
            print("  Wrote %s" % os.path.relpath(path, ROOT))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
