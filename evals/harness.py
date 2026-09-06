"""
PE6201 · A2 scaffold — THE HARNESS  (D4, D5)
====================================================================
Load the answer key, run cases, grade them, report.

--------------------------------------------------------------------
THE TWO KINDS OF CHECK, AND WHY YOU NEED BOTH

A CODE CHECK compares the answer with your answer key.
    decision == expected_decision
    No model, no person, no opinion. Deterministic, free, instant.
    It is what produces the number.

A JUDGEMENT CHECK has someone read the record and decide.
    "Does the reason actually name the band and the window?"
    A PERSON can do it. A SECOND MODEL can do it. Same kind of check -
    the only difference is who grades. (This is what A1 called L1/L2.
    The names never mattered; the difference does.)

Why both: with three possible outcomes, a coin-flip scores 33% on the
code check alone. An agent can reach the right decision for the wrong
reason and the code check will not notice. `must_record` and `trigger`
are what stop a lucky run counting as a good one.

`prepare_judgement_check` below does NOT grade. It builds the queue a
human or a second model works through. Automating the judgement is
your design decision - and if you use a model, say so, because a model
grading a model is a claim that needs defending.
====================================================================
"""
import json
import os
import re
import statistics

import config
from loop_agent import run_case


# =====================================================================
# LOADING
# =====================================================================
def load_key(problem=None):
    """The answer key. YOURS, not ours, once you have extended it.

    Starts as 15 rows and grows by one per case you write. Same file
    throughout - the harness joins on case_id and does not care which
    rows we shipped and which you added.
    """
    problem = problem or config.PROBLEM
    path = os.path.join(config.data_root(),
                        "expected_outcomes_%s.json" % problem)
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {r["case_id"]: r for r in rows}


def load_cases(problem=None):
    """Every case id in the work queue, in file order."""
    problem = problem or config.PROBLEM
    table, field = (("referrals", "referral_id") if problem == "B"
                    else ("claims", "claim_id"))
    path = os.path.join(config.data_root(), "data_%s" % problem,
                        "%s.json" % table)
    with open(path, encoding="utf-8") as fh:
        return [r[field] for r in json.load(fh)]


# =====================================================================
# THE CODE CHECK
# =====================================================================
def code_check(record, expected):
    """Deterministic comparison. Returns (passed, [reasons it failed]).

    Note what is compared and what is NOT. The DECISION and its single
    TRIGGER are compared. The wording is not, the turn count is not, the
    cost is not - two agents can both be right and cost very different
    amounts, which is the subject of D6.
    """
    fails = []

    if record.get("decision") != expected.get("expected_decision"):
        fails.append("decision %r, expected %r"
                     % (record.get("decision"), expected.get("expected_decision")))

    # An escalation must escalate FOR THE RIGHT REASON. A run that
    # reaches the right outcome by the wrong trigger is not a pass - it
    # got there by luck and it will not get there next time.
    if expected.get("trigger"):
        if record.get("trigger") != expected["trigger"]:
            fails.append("trigger %r, expected %r"
                         % (record.get("trigger"), expected["trigger"]))

    # A booking must book the RIGHT slot. Problem B only.
    if expected.get("booked"):
        got = record.get("booked") or {}
        for field in ("clinic", "date", "time"):
            if got.get(field) != expected["booked"][field]:
                fails.append("booked.%s %r, expected %r"
                             % (field, got.get(field), expected["booked"][field]))

    # A REQUEST MUST NAME THE RIGHT THING. Brief D4 lists "the named
    # missing item" as a code check, beside the decision and the trigger.
    # Without this, CLM-9030 - whose whole point is that asking for the
    # pre-authorisation instead of the discharge summary is WRONG - passes
    # on the decision word alone.
    if expected.get("missing"):
        ok, why = _missing_matches(record.get("missing"), expected["missing"])
        if not ok:
            fails.append("missing %r, expected %r (%s)"
                         % (record.get("missing"), expected["missing"], why))

    # THE GATED ACTION FIRED AT MOST ONCE. Brief D4 again. Cheap to check,
    # and it is the difference between a gate and a decoration.
    gated = _gated_action_name()
    if gated:
        fired = [e for e in record.get("evidence", []) if e == gated]
        if len(fired) > 1:
            fails.append("%s fired %d times - the gated action must fire at "
                         "most once" % (gated, len(fired)))
        if fired and record.get("decision") in ("escalate", "request_document",
                                                "request_information"):
            fails.append("%s fired on a %r outcome - nothing should have been "
                         "issued" % (gated, record.get("decision")))

    return (not fails), fails


def _gated_action_name():
    """Imported lazily so this module can also be used to re-score a saved
    results file without dragging in the tool layer."""
    try:
        from tools import tools as _t
        return _t.GATED_ACTION.get(config.PROBLEM)
    except Exception:
        return None


_CODE_RE = re.compile(r"\b(\d{5})\b")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _missing_matches(got, want):
    """Compare two 'named missing item' strings STRUCTURALLY.

    Exact equality is too strict and a substring test is too loose - and
    the loose one is the trap Class 4 showed: a check that passed because
    a date it was looking for happened to appear in an answer that was
    wrong about everything else.

    So compare the things we actually care about, and nothing else:

      * the LINE it belongs to        - the 5-digit procedure code
      * the DATE it must be valid on  - where the label names one
      * WHICH KIND of thing is wanted - a pre-authorisation, or a named
        document, and if a document, which document

    Wording is deliberately NOT compared. Our own key phrases the same
    request three ways - "pre-authorisation reference for line 62480,
    valid on ...", "current pre-authorisation for line 29881, valid on
    ...", "pre-authorisation valid on ... for line 62480" - because six
    people wrote it. Grading prose would fail correct answers and teach
    the team to write to the grader instead of to the member.
    """
    if not got:
        return False, "nothing was named"
    got_s, want_s = str(got).lower(), str(want).lower()

    want_codes = set(_CODE_RE.findall(want_s))
    if want_codes and not (want_codes & set(_CODE_RE.findall(got_s))):
        return False, "does not name line %s" % ", ".join(sorted(want_codes))

    want_dates = set(_DATE_RE.findall(want_s))
    if want_dates and not (want_dates & set(_DATE_RE.findall(got_s))):
        return False, "does not name the date %s" % ", ".join(sorted(want_dates))

    wants_preauth = "pre-authorisation" in want_s or "preauth" in want_s
    got_preauth = "pre-authorisation" in got_s or "preauth" in got_s
    if wants_preauth != got_preauth:
        return False, ("named a document where a pre-authorisation was wanted"
                       if wants_preauth else
                       "named a pre-authorisation where a document was wanted")

    if not wants_preauth:
        doc = want_s.split(" for line")[0].strip()
        if doc and doc not in got_s:
            return False, "does not name the document %r" % doc

    return True, ""


# =====================================================================
# THE JUDGEMENT CHECK
# =====================================================================
def prepare_judgement_check(record, expected):
    """Build ONE item for a human - or a second model - to rule on.

    This deliberately does not decide anything. `must_record` items are
    written in English and a substring match would be theatre, not a
    check. Someone reads the reason and answers yes or no per item.
    """
    return {
        "case_id": record["case_id"],
        "decision": record.get("decision"),
        "reason": record.get("reason", ""),
        "must_record": expected.get("must_record", []),
        "verdict": None,          # <- a person or a second model fills this
        "graded_by": None,        # <- "person: Priya" | "model: <name>"
    }


# =====================================================================
# RUNNING THE SET
# =====================================================================
def run_set(case_ids=None, problem=None, trials_for=None, verbose=False,
            run_one=None, on_result=None, skip=None):
    """Run cases and grade them.

    `trials_for(case_id) -> int` decides how many trials each case gets.
    D4: ordinary cases get ONE trial; NEGATIVE cases get THREE, because
    negatives are the ones that flip between runs and a single trial
    cannot tell a real refusal from a lucky one.

    THE THREE HOOKS EXIST SO THE LIVE BATTERY DOES NOT FORK THIS LOOP.
    Duplicating the 1-vs-3 policy in a second runner would recreate the
    exact drift the battery's whole provenance layer exists to prevent -
    two definitions of "how many trials" is one more than is safe.

      run_one(case_id, problem=, verbose=)  defaults to run_case. The
                  battery passes a wrapper that adds per-trial exception
                  isolation, spend accounting and the budget cap.
      on_result(result)  called after each graded trial, before the next
                  one starts. The battery checkpoints here, so a crash
                  costs one trial rather than the whole run.
      skip  a set of (case_id, trial) already completed. The resume hook.

    All three default to today's behaviour, so run_eval.py and the D2(c)
    experiment are untouched.
    """
    problem = problem or config.PROBLEM
    key = load_key(problem)
    case_ids = case_ids or load_cases(problem)
    trials_for = trials_for or (lambda cid: 3 if _is_negative(key.get(cid)) else 1)
    run_one = run_one or run_case
    skip = skip or set()

    results, judgement_queue = [], []

    for cid in case_ids:
        expected = key.get(cid)
        if expected is None:
            # check_my_data.py catches this before you get here. If you
            # are seeing it, run the checker.
            print("  SKIP %s - no label in the answer key" % cid)
            continue

        for trial in range(1, trials_for(cid) + 1):
            if (cid, trial) in skip:
                continue
            record = run_one(cid, problem=problem, verbose=verbose)
            passed, fails = code_check(record, expected)
            result = {"case_id": cid, "trial": trial, "passed": passed,
                      "fails": fails, "record": record,
                      "family": expected.get("family")}
            results.append(result)
            if on_result is not None:
                on_result(result)
            if trial == 1:
                judgement_queue.append(prepare_judgement_check(record, expected))

    return results, judgement_queue


def is_negative(expected):
    """Public alias. build_plan and the battery aggregator must share ONE
    definition of "negative" with the trial policy above - three copies of
    this list is three chances to disagree about the trial count."""
    return _is_negative(expected)


def _is_negative(expected):
    """A negative case is one whose correct outcome is anything except
    the act - so, an ask or an escalate."""
    if not expected:
        return False
    return expected.get("expected_decision") in (
        "escalate", "request_document", "request_information")


# =====================================================================
# REPORTING
# =====================================================================
def report(results):
    """The result table. EVERY pass rate is printed with its trial count,
    because a pass rate without one is not a measurement."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    turns = [r["record"]["turns"] for r in results]
    cost = sum(r["record"]["cost_usd"] for r in results)

    print()
    print("=" * 68)
    print("  RESULTS   %d of %d trials passed   (%.0f%%)"
          % (passed, total, 100.0 * passed / total if total else 0))
    print("=" * 68)
    print("  trials              %d" % total)
    print("  median turns        %s" % (statistics.median(turns) if turns else "-"))
    print("  worst case turns    %s" % (max(turns) if turns else "-"))
    print("  hit the step cap    %d"
          % sum(1 for r in results if r["record"]["stopped_by"] == "step_cap"))
    print("  total cost          US$%.4f   (%s backend)"
          % (cost, results[0]["record"]["backend"] if results else "-"))
    print()

    failures = [r for r in results if not r["passed"]]
    if failures:
        print("  FAILED TRIALS - each one is either a bug or a wrong label:")
        for r in failures:
            print("    %-12s trial %d  [%s]" % (r["case_id"], r["trial"],
                                                r["family"]))
            for f in r["fails"]:
                print("        %s" % f)
        print()
        print("  Before you fix the agent, ask whether the LABEL is right.")
        print("  Test: could you justify the label to someone who had never")
        print("  seen your agent's output, using only Appendix A's routing")
        print("  table? If yes, the agent is wrong. If no, the label is.")
    else:
        print("  Every trial passed the code check.")
        print("  That is HALF the check. Work through the judgement queue")
        print("  before you believe this number.")
    print()
    return {"trials": total, "passed": passed,
            "pass_rate": passed / total if total else 0.0,
            "median_turns": statistics.median(turns) if turns else None,
            "cost_usd": cost}
