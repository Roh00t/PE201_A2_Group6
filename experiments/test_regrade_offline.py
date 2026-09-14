#!/usr/bin/env python3
"""
PE6201 · A2 — THE OFFLINE RE-GRADE, CHECKED  (D4)
====================================================================
    python3 experiments/test_regrade_offline.py

A grader change is a measurement change, so it gets the same treatment
as any other: each fix is shown to rescue what it claims to rescue, and
to rescue nothing else. No network, no key, no cost.
====================================================================
"""
import glob
import hashlib
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from experiments import regrade_offline as rg              # noqa: E402

PASSED, FAILED = [], []

# The evals/harness.py every committed battery was graded with. Pinned here
# so these checks keep testing the FIXES, not whatever harness.py says after
# the post-freeze patch has already moved the fixes into it.
FROZEN_HARNESS_SHA = "6ce395063fe5e101d711b02b6020f072d728eaaabdd547737cce4e38c6547668"
FROZEN, _ = rg.load_grader(FROZEN_HARNESS_SHA)


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(name)
    print("  %s  %s%s" % ("PASS" if condition else "FAIL", name,
                          ("   " + str(detail)) if detail and not condition else ""))


DOC_KEY = {"expected_decision": "request_document",
           "missing": "itemised bill for line 45378"}
PREAUTH_KEY = {"expected_decision": "request_document",
               "missing": "current pre-authorisation for line 29881, valid on 2026-09-09"}
APPROVE_KEY = {"expected_decision": "approve_in_principle"}


def approval(evidence, turn_tokens=((3000, 100), (3300, 50), (3600, 60)),
             gate_passed=True):
    return {"decision": "approve_in_principle", "evidence": list(evidence),
            "turn_tokens": [list(t) for t in turn_tokens],
            "guardrails_fired": ([{"guardrail": "gate_passed", "detail": "x"}]
                                 if gate_passed else [])}


def sent_row(case_id, tokens_in, tokens_out, backend="live",
             decision="approve_in_principle"):
    return {"case_id": case_id, "decision": decision, "backend": backend,
            "tokens_in": tokens_in, "tokens_out": tokens_out}


# =====================================================================
# FIX 1 · UNDERSCORES
# =====================================================================
def scenario_underscore_rescues_the_tool_identifier():
    print("\n  1 · underscore fix rescues the document spelled as the tool spells it")
    rec = {"decision": "request_document",
           "missing": "itemised_bill for code 45378 on 2026-09-10"}
    before, _ = rg.code_check(rec, DOC_KEY, grader=FROZEN)
    after, fails = rg.code_check(rec, DOC_KEY, underscore=True, grader=FROZEN)
    check("frozen harness fails 'itemised_bill'", before is False)
    check("underscore fix passes it", after is True, fails)

    as_dict = {"decision": "request_document",
               "missing": {"item": "itemised_bill", "line_code": "45378"}}
    check("a dict-shaped missing item is rescued too",
          rg.code_check(as_dict, DOC_KEY, underscore=True, grader=FROZEN)[0] is True)


def scenario_underscore_rescues_nothing_else():
    print("\n  2 · underscore fix does not loosen the comparison")
    wrong_doc = {"decision": "request_document",
                 "missing": "discharge_summary for code 45378"}
    check("the wrong document still fails",
          rg.code_check(wrong_doc, DOC_KEY, underscore=True, grader=FROZEN)[0] is False)
    wrong_line = {"decision": "request_document",
                  "missing": "itemised_bill for code 99213"}
    check("the right document on the wrong line still fails",
          rg.code_check(wrong_line, DOC_KEY, underscore=True, grader=FROZEN)[0] is False)
    preauth_asked_as_doc = {"decision": "request_document",
                            "missing": "itemised_bill for code 29881 on 2026-09-09"}
    check("a document named where a pre-authorisation was wanted still fails",
          rg.code_check(preauth_asked_as_doc, PREAUTH_KEY, underscore=True, grader=FROZEN)[0] is False)
    right_preauth = {"decision": "request_document",
                     "missing": {"item": "pre-authorisation", "line_code": "29881",
                                 "date": "2026-09-09"}}
    check("a correct pre-authorisation request passes with and without the fix",
          rg.code_check(right_preauth, PREAUTH_KEY, grader=FROZEN)[0] is True
          and rg.code_check(right_preauth, PREAUTH_KEY, underscore=True, grader=FROZEN)[0] is True)
    # The declared fix is underscores -> spaces, and nothing wider. The
    # harness looks for "pre-authorisation" with a hyphen, so a model that
    # writes "pre_authorisation" is NOT rescued. No committed record does;
    # this pins the limit so nobody widens the fix without declaring it.
    underscored_preauth = {"decision": "request_document",
                           "missing": {"item": "pre_authorisation", "code": "29881",
                                       "date": "2026-09-09"}}
    check("LIMIT: 'pre_authorisation' is not rescued - the fix is underscores only",
          rg.code_check(underscored_preauth, PREAUTH_KEY, underscore=True, grader=FROZEN)[0] is False)
    nothing = {"decision": "request_document", "missing": None}
    check("naming nothing still fails",
          rg.code_check(nothing, DOC_KEY, underscore=True, grader=FROZEN)[0] is False)
    wrong_decision = {"decision": "escalate", "missing": "itemised_bill for 45378"}
    check("the decision is still compared exactly",
          rg.code_check(wrong_decision, DOC_KEY, underscore=True, grader=FROZEN)[0] is False)


# =====================================================================
# FIX 2 · THE LETTER WAS SENT
# =====================================================================
def scenario_letter_rule_reads_the_ledger():
    print("\n  3 · letter rule reads the ledger, not the call list")
    rec = approval(["get_claim", "check_coverage", "issue_decision_letter"])
    # running totals of the default turn_tokens: (3000,100) (6300,150) (9900,210)
    led = rg.Ledger([sent_row("CLM-1", 6300, 150)], backend="live")
    check("a matching sent row counts as sent",
          rg.letter_sent(rec, "CLM-1", led)[0] is True)

    blocked = rg.Ledger([], backend="live")
    sent, how = rg.letter_sent(rec, "CLM-1", blocked)
    check("a call with no sent row (a BLOCKED letter) is not sent",
          sent is False and "no sent row" in how, how)

    never = approval(["get_claim", "check_coverage"])
    check("an approval that never called the letter is not sent",
          rg.letter_sent(never, "CLM-1", led)[0] is False)

    scripted = rg.Ledger([sent_row("CLM-1", 6300, 150, backend="scripted")],
                         backend="live")
    check("a scripted preflight row cannot stand in for a live trial",
          rg.letter_sent(rec, "CLM-1", scripted)[0] is False)

    other_case = rg.Ledger([sent_row("CLM-2", 6300, 150)], backend="live")
    check("another case's row cannot stand in",
          rg.letter_sent(rec, "CLM-1", other_case)[0] is False)

    canary = rg.Ledger([sent_row("CLM-1", 4321, 99)], backend="live")
    check("a row whose token stamp matches no point in this trial is not claimed",
          rg.letter_sent(rec, "CLM-1", canary)[0] is False)

    escalate_letter = rg.Ledger([sent_row("CLM-1", 6300, 150, decision="escalate")],
                                backend="live")
    check("a letter that sent the wrong decision does not count as the approval",
          rg.letter_sent(rec, "CLM-1", escalate_letter)[0] is False)


def scenario_one_row_one_trial():
    print("\n  4 · one ledger row satisfies exactly one trial")
    t1 = approval(["issue_decision_letter"], turn_tokens=((1000, 10), (1100, 20)))
    t2 = approval(["issue_decision_letter"], turn_tokens=((1000, 10), (1100, 20)))
    led = rg.Ledger([sent_row("CLM-1", 2100, 30)], backend="live")
    first = rg.letter_sent(t1, "CLM-1", led)[0]
    second = rg.letter_sent(t2, "CLM-1", led)[0]
    check("two identical trials cannot both claim one sent row",
          first is True and second is False, (first, second))


def scenario_no_ledger_is_approximate():
    print("\n  5 · a run with no ledger is graded approximately, and says so")
    rec = approval(["issue_decision_letter"], gate_passed=True)
    sent, how = rg.letter_sent(rec, "CLM-1", None)
    check("gate_passed stands in", sent is True)
    check("and the result is labelled APPROXIMATE", "APPROXIMATE" in how, how)
    held = approval(["issue_decision_letter"], gate_passed=False)
    check("no gate_passed is not sent", rg.letter_sent(held, "CLM-1", None)[0] is False)


def scenario_letter_rule_scope():
    print("\n  6 · the letter rule only ever touches approvals")
    doc = {"member": "nobody", "run_id": "no-ledger", "backend": "live",
           "results": [
               {"case_id": "CLM-8901", "trial": 1, "passed": True,
                "record": {"decision": "request_document",
                           "missing": "itemised bill for line 45378",
                           "evidence": ["get_claim"], "turns": 2}},
           ]}
    run = rg.regrade_run(doc, {"CLM-8901": DOC_KEY})
    s = run["summaries"]
    check("a correct request is unaffected by the letter rule",
          s["letter_rule"]["passed"] == 1 and s["both"]["passed"] == 1, s)


# =====================================================================
# THE COMMITTED RUNS
# =====================================================================
def _run(result, run_id):
    return next((r for r in result["runs"] if r["run_id"] == run_id), None)


def scenario_committed_runs():
    print("\n  7 · the committed batteries re-grade to the numbers in the report")
    paths = [p for p in rg.discover()
             if os.path.basename(p[0]).endswith(("8f968b0d3782.json",
                                                 "d05a3189ca96.json"))]
    if len(paths) < 2:
        print("  (skipped - the two committed current-harness batteries are absent)")
        return
    result = rg.regrade_all(paths)
    hy, rp = _run(result, "8f968b0d3782"), _run(result, "d05a3189ca96")

    def neg(run, variant):
        n = run["summaries"][variant]["negative"]
        return round(n["rate"] * n["trials"]), n["trials"]

    check("both runs re-score identically to their recorded grades",
          hy["rescored_matches_recorded"] and rp["rescored_matches_recorded"])
    check("both runs have an exact ledger",
          hy["letter_rule_exact"] and rp["letter_rule_exact"])
    check("gpt-4.1-mini negative 18/30 as recorded", neg(hy, "recorded") == (18, 30),
          neg(hy, "recorded"))
    check("gpt-4.1-mini negative 21/30 (70%) with the underscore fix alone",
          neg(hy, "underscore") == (21, 30), neg(hy, "underscore"))
    check("gpt-4.1-mini overall 43/60 with the letter rule alone",
          hy["summaries"]["letter_rule"]["passed"] == 43,
          hy["summaries"]["letter_rule"]["passed"])
    check("gpt-4.1-mini overall 46/60 with both",
          hy["summaries"]["both"]["passed"] == 46, hy["summaries"]["both"]["passed"])
    moved = sorted((c["case_id"], c["fix"]) for c in hy["changes"])
    check("gpt-4.1-mini: exactly CLM-8901 x3 rescued and 5 letter-less approvals failed",
          moved.count(("CLM-8901", "underscore")) == 3
          and sum(1 for m in moved if m[1] == "letter_rule") == 5
          and len(moved) == 8, moved)
    check("Haiku 4.5 negative 27/30 with the underscore fix",
          neg(rp, "underscore") == (27, 30), neg(rp, "underscore"))
    check("Haiku 4.5 loses nothing to the letter rule",
          rp["summaries"]["letter_rule"]["passed"] == rp["summaries"]["rescored"]["passed"])


def scenario_graded_with_the_runs_own_harness():
    print("\n  7b · a run is re-scored by the harness that graded it, not today's")
    check("the vendored copy of the frozen harness is hash-verified and loads",
          FROZEN is not rg.harness and hasattr(FROZEN, "code_check"))
    paths = [p for p in rg.discover()
             if os.path.basename(p[0]).endswith("8f968b0d3782.json")]
    if not paths:
        print("  (skipped - gpt-4.1-mini's battery is absent)")
        return

    saved, saved_cache = rg.harness, dict(rg._GRADERS)

    class AlreadyFixed(object):
        """Stands in for evals/harness.py AFTER the post-freeze merge: a
        code_check that grades differently, everything else unchanged."""
        def __getattr__(self, name):
            return getattr(saved, name)

        @staticmethod
        def code_check(record, expected):
            return True, []

    rg.harness, rg._GRADERS = AlreadyFixed(), {}
    try:
        run = rg.regrade_all(paths)["runs"][0]
    finally:
        rg.harness, rg._GRADERS = saved, saved_cache
    check("today's harness changing does not move the re-scored baseline",
          run["rescored_matches_recorded"] and run["summaries"]["rescored"]["passed"] == 48,
          run["summaries"]["rescored"]["passed"])
    check("and the row says which harness graded it",
          "vendored" in run["graded_with"], run["graded_with"])


def scenario_windows_checkout_harness():
    print("\n  7c · a run from a Windows checkout is re-scored by the same harness")
    with open(os.path.join(rg.FROZEN_GRADERS, "harness_%s.py" % FROZEN_HARNESS_SHA[:12]), "rb") as fh:
        crlf = hashlib.sha256(fh.read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
    module, how = rg.load_grader(crlf)
    check("the CRLF hash of the frozen harness loads the vendored copy, not today's",
          module is not rg.harness and "vendored" in how and "Windows" in how, how)
    other = crlf[:-1] + ("0" if crlf[-1] != "0" else "1")
    module, how = rg.load_grader(other)
    check("a hash that matches neither form still falls back, and says so",
          module is rg.harness and "TODAY'S" in how, how)

    paths = [p for p in rg.discover()
             if os.path.basename(p[0]).endswith(("014683ddcc79.json", "30c46384999a.json"))]
    if len(paths) < 2:
        print("  (skipped - shen_bowen's and xia_yanran's batteries are absent)")
        return
    result = rg.regrade_all(paths)
    for run_id, member, recorded in (("014683ddcc79", "shen_bowen", 48),
                                     ("30c46384999a", "xia_yanran", 44)):
        run = _run(result, run_id)
        check("%s re-scores to its recorded %d/60 with its own harness" % (member, recorded),
              run["rescored_matches_recorded"]
              and run["summaries"]["rescored"]["passed"] == recorded
              and "vendored" in run["graded_with"],
              (run["summaries"]["rescored"]["passed"], run["graded_with"]))


def scenario_reads_only():
    print("\n  8 · the re-grade changes no battery file and no ledger")
    watched = (glob.glob(os.path.join(ROOT, "results", "live", "battery__*.json"))
               + glob.glob(os.path.join(ROOT, "results", "archive", "live", "*.json"))
               + glob.glob(os.path.join(ROOT, "logs", "battery", "*.jsonl")))

    def digest():
        return {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in watched}

    before = digest()
    result = rg.regrade_all()
    rg.render(result, show_trials=True)
    check("every battery file and ledger is byte-identical afterwards",
          digest() == before)


def scenario_deterministic_output():
    print("\n  9 · two re-grades write byte-identical files")
    saved = rg.OUT_DIR
    try:
        blobs = []
        for _ in range(2):
            rg.OUT_DIR = tempfile.mkdtemp()
            paths = rg.write(rg.regrade_all())
            blobs.append([open(p, "rb").read() for p in paths])
        check("identical JSON and Markdown on a second run", blobs[0] == blobs[1])
    finally:
        rg.OUT_DIR = saved


def main():
    print("=" * 72)
    print("  OFFLINE RE-GRADE - checked")
    print("=" * 72)
    for scenario in (scenario_underscore_rescues_the_tool_identifier,
                     scenario_underscore_rescues_nothing_else,
                     scenario_letter_rule_reads_the_ledger,
                     scenario_one_row_one_trial,
                     scenario_no_ledger_is_approximate,
                     scenario_letter_rule_scope,
                     scenario_committed_runs,
                     scenario_graded_with_the_runs_own_harness,
                     scenario_windows_checkout_harness,
                     scenario_reads_only,
                     scenario_deterministic_output):
        scenario()
    print("\n" + "=" * 72)
    print("  %d passed, %d failed" % (len(PASSED), len(FAILED)))
    print("=" * 72)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
