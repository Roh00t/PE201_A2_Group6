#!/usr/bin/env python3
"""
PE6201 · A2 — THE BATTERY TABLE  (D5b -> report section 3, and D6)
====================================================================
    python3 evals/aggregate_battery.py

Free. Reads every results/live/battery__*.json and emits the table the
report needs, plus the v1-vs-v2 delta D2(b) rests on.

WHY THIS IS A SEPARATE SCRIPT. Six people appending to one CSV is six
merge conflicts. Each member writes their own file; this reads them all
and can be regenerated at any time, including after somebody re-runs.

THE FIRST THING IT DOES IS CHECK THE SIX AGREE. If two members ran
different answer keys the table would still render, still look right,
and be meaningless. A comparison across drifted runs is worse than no
comparison, because it is publishable.

TWO NEGATIVE NUMBERS, NOT ONE. The negative TRIAL rate and the negative
3-OF-3 rate are different findings, and the 3x trial policy exists to
produce the second. A model at 90% trial / 70% three-of-three is
unreliable on refusals; one at 90%/90% is consistently wrong about one
case. Reporting only the trial rate throws away the reason the negatives
cost three times as much to run.
====================================================================
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_DIR = os.path.join(ROOT, "results", "live")


def load(include_dry=False):
    pattern = os.path.join(LIVE_DIR, "battery__*.json")
    files = sorted(glob.glob(pattern))
    if include_dry:
        files += sorted(glob.glob(os.path.join(LIVE_DIR, "dryrun",
                                               "battery__*.json")))
    out = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            out.append((f, json.load(fh)))
    return out


def check_comparable(runs):
    """Every run must share the parts of the fingerprint that are not
    supposed to vary. The model, the prompt version and the prices are
    the variables; everything else is the experiment."""
    problems = []
    shared = ("answer_key_sha256", "fixtures_sha256", "plan_sha256")
    seen = {}
    for path, r in runs:
        fp = r.get("fingerprint") or {}
        for k in shared:
            seen.setdefault(k, {}).setdefault(fp.get(k), []).append(r["member"])
        if r.get("overrides"):
            problems.append(
                "%s ran with %d override(s): %s"
                % (r["member"], len(r["overrides"]),
                   "; ".join("%s (%s)" % (o["check"], o["reason"])
                             for o in r["overrides"])))
    for k, groups in seen.items():
        if len(groups) > 1:
            problems.append(
                "%s DIFFERS between members: %s - these runs are not "
                "comparable and the table below is not a comparison."
                % (k, " vs ".join("%s=%s" % (",".join(v), (g or "?")[:8])
                                  for g, v in groups.items())))
    return problems


def rows(runs):
    out = []
    for _path, r in runs:
        s = r["summary"]
        n = s["negative"]
        out.append({
            "member": r["member"],
            "model": r["model"],
            "tier": r.get("tier"),
            "family": r.get("family"),
            "prompt": r["prompt_version"],
            "trials": s["trials_graded"],
            "pass_rate": s["pass_rate"],
            "ordinary": s["ordinary"]["rate"],
            "neg_trials": n["rate"],
            "neg_3of3": n["consistency"],
            "neg_cases": "%d/%d" % (n["cases_3of3"], n["cases"]),
            "median_turns": s["median_turns"],
            "transport": s["trials_transport_failed"],
            "tokens_in": s["tokens_in"],
            "tokens_out": s["tokens_out"],
            "cost": s["cost_usd"],
            "cost_per_trial": (s["cost_usd"] / s["trials_graded"]
                               if s["trials_graded"] else 0.0),
            "clean": r.get("clean", True),
            "dry_run": r.get("dry_run", False),
        })
    return sorted(out, key=lambda x: (x["prompt"], x["tier"] or "", x["cost"]))


HEAD = ("member", "model", "tier", "prompt", "trials", "pass", "ordinary",
        "neg trial", "neg 3of3", "med turns", "tok in", "tok out", "US$")


def to_markdown(rs):
    lines = ["| " + " | ".join(HEAD) + " |",
             "|" + "|".join(["---"] * len(HEAD)) + "|"]
    for r in rs:
        lines.append("| " + " | ".join([
            r["member"] + ("" if r["clean"] else " ⚠"),
            "`%s`" % r["model"], r["tier"] or "", r["prompt"],
            str(r["trials"]),
            "%.1f%%" % (100 * r["pass_rate"]),
            "%.1f%%" % (100 * r["ordinary"]),
            "%.1f%%" % (100 * r["neg_trials"]),
            "%s (%.0f%%)" % (r["neg_cases"], 100 * r["neg_3of3"]),
            str(r["median_turns"]),
            "{:,}".format(r["tokens_in"]), "{:,}".format(r["tokens_out"]),
            "%.4f" % r["cost"]]) + " |")
    return "\n".join(lines)


def to_csv(rs):
    keys = ["member", "model", "family", "tier", "prompt", "trials",
            "pass_rate", "ordinary", "neg_trials", "neg_3of3", "neg_cases",
            "median_turns", "transport", "tokens_in", "tokens_out", "cost",
            "cost_per_trial", "clean", "dry_run"]
    out = [",".join(keys)]
    for r in rs:
        out.append(",".join('"%s"' % r[k] if isinstance(r[k], str) else str(r[k])
                            for k in keys))
    return "\n".join(out)


def v1_vs_v2(rs):
    """D2(b): the same model, two prompt versions. The ONLY measurement
    in A2 that isolates our own writing as the variable."""
    v1 = [r for r in rs if r["prompt"] == "v1"]
    if not v1:
        return None
    a = v1[0]
    b = next((r for r in rs if r["prompt"] == "v2" and r["model"] == a["model"]),
             None)
    if not b:
        return ("The v1 pass ran on %s, which no v2 member ran. Comparing "
                "prompt versions means holding the model fixed, so this pair "
                "measures two variables at once and cannot be reported."
                % a["model"])
    d = lambda k: b[k] - a[k]
    return ("\n  v1 -> v2 on %s, model held fixed (%s -> %s)\n"
            "    pass rate       %.1f%%  ->  %.1f%%   (%+.1f pp)\n"
            "    negative 3of3   %.1f%%  ->  %.1f%%   (%+.1f pp)\n"
            "    input tokens    %s  ->  %s   (%+.1f%%)\n"
            "    cost per trial  US$%.5f  ->  US$%.5f\n"
            % (a["model"], a["member"], b["member"],
               100 * a["pass_rate"], 100 * b["pass_rate"], 100 * d("pass_rate"),
               100 * a["neg_3of3"], 100 * b["neg_3of3"], 100 * d("neg_3of3"),
               "{:,}".format(a["tokens_in"]), "{:,}".format(b["tokens_in"]),
               100.0 * (b["tokens_in"] - a["tokens_in"]) / max(1, a["tokens_in"]),
               a["cost_per_trial"], b["cost_per_trial"]))


def main(argv=None):
    argv = argv or sys.argv[1:]
    include_dry = "--include-dry-run" in argv
    runs = load(include_dry)
    if not runs:
        print("\n  No battery results in results/live/ yet.")
        print("  Rehearse first:  python3 evals/test_battery_fake.py")
        print("  Then dry-run  :  python3 run_battery.py --member <name> "
              "--dry-run\n")
        return 1

    print()
    print("=" * 78)
    print("  D5(b) BATTERY - %d run(s)" % len(runs))
    print("=" * 78)

    problems = check_comparable(runs)
    if problems:
        print("\n  READ THIS BEFORE USING THE TABLE:\n")
        for p in problems:
            print("    ! %s" % p)
        print()

    rs = rows(runs)
    print(to_markdown(rs))
    print()
    shape = runs[0][1]["fingerprint"]["plan_shape"]
    print("  %d cases, %d negative, %d trials per member. Every rate above is "
          "quoted\n  with its trial count because a pass rate without one is "
          "not a measurement." % (shape["cases"], shape["negative"],
                                  shape["trials"]))
    delta = v1_vs_v2(rs)
    if delta:
        print(delta)

    md = os.path.join(LIVE_DIR, "battery_table.md")
    csv = os.path.join(LIVE_DIR, "battery_table.csv")
    os.makedirs(LIVE_DIR, exist_ok=True)
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(to_markdown(rs) + "\n")
        if delta:
            fh.write("\n```" + delta + "```\n")
    with open(csv, "w", encoding="utf-8") as fh:
        fh.write(to_csv(rs) + "\n")
    print("  Wrote %s and %s\n" % (os.path.relpath(md, ROOT),
                                   os.path.relpath(csv, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
