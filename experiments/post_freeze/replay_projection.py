#!/usr/bin/env python3
"""
PE6201 · A2 — WHAT THE UPGRADE WOULD HAVE DONE TO THE RECORDED BATTERIES
====================================================================
    python3 experiments/post_freeze/stage.py --check     (runs this for you)

Runs ONLY in a tree with post_freeze.patch applied - it imports
src/final_check.py, which the frozen tree does not have. stage.py --check
applies the patch in a throwaway clone and runs this there.

WHAT IT DOES. Takes every trial of the committed current-harness batteries
and asks what the upgraded harness would have concluded about the SAME
model behaviour:

  1 · every letter the model actually sent is re-sent to the upgraded
      issue_decision_letter with the arguments it really used (read from
      that run's decision ledger) - does one of the new checks refuse it?
  2 · the fact ledger is rebuilt from the tools the model called;
  3 · the final record goes through final_check.validate;
  4 · the result is graded by the upgraded harness.

Each trial lands in one of two kinds:

  DETERMINISTIC   code decides the outcome with no further model reply -
                  an injection override, a record the check accepts, a
                  halt or unparseable reply the check never touches.
  NEEDS A REPAIR  the final check would send the record back once. What the
                  model writes next cannot be replayed, so the trial is
                  counted as a FAIL in the lower bound and a PASS in the
                  upper bound. The real figure is in between and has to be
                  measured live.

WHAT IT CANNOT KNOW, STATED PLAINLY. The upgraded tools RETURN MORE -
get_preauthorisation says why none applies, check_duplicate_claim names
near misses. A model that reads more may choose differently, better or
worse. This replay holds the model's choices fixed, so it is a projection
of the harness, not a measurement of any model. The v3 battery is the
measurement.
====================================================================
"""
import argparse
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

try:
    import final_check                                     # noqa: E402
except ImportError:
    sys.exit("\n  This tree does not have the post-freeze patch applied.\n"
             "  Run:  python3 experiments/post_freeze/stage.py --check\n")

from evals import harness                                  # noqa: E402
from evals.run_battery import aggregate                    # noqa: E402
from experiments import regrade_offline as rg              # noqa: E402
from tools import tools                                    # noqa: E402

GATED = "issue_decision_letter"
UNPARSEABLE = "did not return parseable JSON"


def rebuild_ledger(case_id, record, sent_ok):
    """The facts the upgraded ledger would have held, from the calls made."""
    ledger = final_check.FactLedger(case_id)
    claim = tools.get_claim(case_id)
    called = record.get("evidence") or []
    if "get_claim" in called:
        ledger.observe("get_claim", {"claim_id": case_id}, claim)
    if "lookup_policy" in called:
        ledger.observe("lookup_policy", {}, tools.lookup_policy(claim["member_id"]))
    if "lookup_hospital" in called:
        ledger.observe("lookup_hospital", {}, tools.lookup_hospital(claim["hospital_id"]))
    if "check_duplicate_claim" in called:
        ledger.observe("check_duplicate_claim", {}, tools.check_duplicate_claim(
            claim["member_id"], claim["hospital_id"], claim["date_of_service"],
            claim["lines"]))
    policy = ledger.policy or tools.lookup_policy(claim["member_id"]) or {}
    policy_id = (policy.get("policy") or {}).get("policy_id")
    checked = called.count("check_coverage")
    for line in (claim["lines"][:checked] if policy_id else []):
        ledger.observe("check_coverage", {"code": line["code"]},
                       tools.check_coverage(line["code"], policy_id, claim.get("documents")))
    if sent_ok is not None:
        ledger.observe(GATED, {}, {"sent": sent_ok})
    return ledger


def resend_letter(case_id, record, row):
    """Re-send a letter the model really sent, through the upgraded checks."""
    claim = tools.get_claim(case_id)
    checked = (record.get("evidence") or [])[:(record.get("evidence") or []).index(GATED)]
    coverage_checked = [l["code"] for l in claim["lines"][:checked.count("check_coverage")]]
    saved = tools.DECISION_LOG_PATH
    with tempfile.TemporaryDirectory() as tmp:
        tools.DECISION_LOG_PATH = os.path.join(tmp, "decisions.jsonl")
        try:
            tools.reset_decision_state()
            tools.set_run_context(coverage_checked=coverage_checked)
            return tools.issue_decision_letter(
                case_id, row["decision"], lines_resolved=row.get("lines_resolved"),
                approved_total=row.get("approved_total"),
                refused_total=row.get("refused_total", 0))
        finally:
            tools.DECISION_LOG_PATH = saved
            tools.reset_decision_state()


def project_trial(result, key, ledger_rows):
    case_id, record = result["case_id"], dict(result.get("record") or {})
    expected = key[case_id]

    sent_ok, letter_note = None, None
    if GATED in (record.get("evidence") or []):
        row = ledger_rows.claim(case_id, record) if ledger_rows else None
        if row is None:
            sent_ok, letter_note = False, "letter was not sent in the recorded run"
        else:
            outcome = resend_letter(case_id, record, row)
            sent_ok = bool(outcome.get("sent"))
            letter_note = ("upgraded letter still sends" if sent_ok else
                           "upgraded letter refuses: %s" % outcome.get("error", "")[9:90])

    untouched = (record.get("stopped_by") or UNPARSEABLE in str(record.get("reason")))
    ledger = rebuild_ledger(case_id, record, sent_ok)
    record["letter_sent"] = ledger.letter_sent
    if untouched:
        ok, _ = harness.code_check(record, expected)
        return {"kind": "deterministic", "lower": ok, "upper": ok,
                "why": "halt or unparseable reply - the final check does not run",
                "letter": letter_note}

    verdict = final_check.validate(record, ledger, fallback_claim=tools.get_claim(case_id))
    if verdict.overridden:
        ok, _ = harness.code_check(verdict.record, expected)
        return {"kind": "deterministic", "lower": ok, "upper": ok,
                "why": "injection override: code escalates", "letter": letter_note}
    if verdict.problems:
        return {"kind": "needs_repair", "lower": False, "upper": True,
                "why": "sent back once: " + verdict.problems[0][:90],
                "letter": letter_note}
    ok, fails = harness.code_check(verdict.record, expected)
    return {"kind": "deterministic", "lower": ok, "upper": ok,
            "why": "accepted" + ("" if ok else ": " + "; ".join(fails)[:90]),
            "letter": letter_note}


def project_run(path):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    key = harness.load_key("A")
    ledger_rows = rg.Ledger.for_run(doc)
    trials, lower, upper = [], [], []
    for r in doc["results"]:
        p = project_trial(r, key, ledger_rows)
        trials.append(dict(p, case_id=r["case_id"], trial=r["trial"],
                           recorded=bool(r["passed"])))
        lower.append({"case_id": r["case_id"], "passed": p["lower"], "record": r["record"]})
        upper.append({"case_id": r["case_id"], "passed": p["upper"], "record": r["record"]})
    recorded = [{"case_id": r["case_id"], "passed": bool(r["passed"]), "record": r["record"]}
                for r in doc["results"]]
    pick = lambda s: {"passed": s["passed"], "trials": s["trials_graded"],
                      "ordinary": s["ordinary"], "negative": s["negative"]}
    return {"member": doc["member"], "model": doc["model"], "run_id": doc["run_id"],
            "recorded": pick(aggregate(recorded, key)),
            "lower": pick(aggregate(lower, key)),
            "upper": pick(aggregate(upper, key)),
            "needs_repair": sum(1 for t in trials if t["kind"] == "needs_repair"),
            "trials": trials}


def _frac(s, part=None):
    if part is None:
        return "%d/%d %.1f%%" % (s["passed"], s["trials"], 100.0 * s["passed"] / s["trials"])
    g = s[part]
    n = round(g["rate"] * g["trials"])
    return "%d/%d %.1f%%" % (n, g["trials"], 100.0 * g["rate"])


def render(runs, show_trials=False):
    out = ["=" * 96,
           "  PROJECTION - the recorded batteries, through the upgraded harness",
           "  (model choices held fixed; 'needs repair' trials bound the range)",
           "=" * 96,
           "  %-40s %-17s %-16s %-16s %s" % ("run", "", "all", "ordinary", "negative")]
    for run in runs:
        out.append("  " + "-" * 94)
        label = "%s · %s" % (run["member"], run["model"])
        for i, (name, title) in enumerate((("recorded", "recorded (frozen)"),
                                           ("lower", "upgraded, lower"),
                                           ("upper", "upgraded, upper"))):
            s = run[name]
            out.append("  %-40s %-17s %-16s %-16s %s"
                       % (label if i == 0 else ("%d trial(s) need a repair" % run["needs_repair"]
                                                if i == 1 else ""),
                          title, _frac(s), _frac(s, "ordinary"), _frac(s, "negative")))
    out.append("")
    if show_trials:
        for run in runs:
            moved = [t for t in run["trials"]
                     if t["lower"] != t["recorded"] or t["upper"] != t["recorded"]]
            out.append("  %s · %s - trials whose grade the upgrade changes" % (run["member"], run["model"]))
            for t in moved:
                out.append("    %-9s t%s  %-13s recorded %-4s -> lower %-4s upper %-4s  %s"
                           % (t["case_id"], t["trial"], t["kind"],
                              "PASS" if t["recorded"] else "FAIL",
                              "PASS" if t["lower"] else "FAIL",
                              "PASS" if t["upper"] else "FAIL", t["why"][:60]))
                if t.get("letter") and "refuses" in t["letter"]:
                    out.append("    %s %s" % (" " * 16, t["letter"][:80]))
            out.append("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="replay_projection.py")
    ap.add_argument("--trials", action="store_true")
    ap.add_argument("--json", help="also write the projection here")
    args = ap.parse_args(argv)
    paths = [p for p, archived in rg.discover() if not archived]
    if not paths:
        print("\n  No current-harness batteries under results/live/.\n")
        return 1
    runs = [project_run(p) for p in paths]
    print()
    print(render(runs, show_trials=args.trials))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(runs, fh, indent=2, sort_keys=True, ensure_ascii=False, default=str)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
