#!/usr/bin/env python3
"""
PE6201 · A2 — WHICH KIND OF CHECK GRADED THIS CASE  (D4)
====================================================================
D4: "Two kinds of check, and you need both." And: "your results table
must say WHICH CHECK each case used."

That classification is what this module adds. It does NOT reimplement
grading - evals/harness.py already does that correctly, and a second
implementation of the same comparison is a second answer to the same
question.

THE RULE, from the brief, quoted:

    "the decision and the trigger are code checks; the wording is a
     judgement check."

A field whose correct value comes from a fixed list is a code check,
always. A field written in prose is a judgement check, always. The
dividing line is not difficulty - it is whether a machine comparing two
values can be wrong about what it just compared.

WHY `must_record` IS NEVER CODE-CHECKED HERE. It reads like something
you could grep for. "approved_total 2180" is right there in the reason
string. But a substring test passes for the WRONG REASON the moment the
agent writes "approved_total 2180 was not reached" - and the FAQ warns
about exactly this trap: check the thing you care about, not a string
that usually accompanies it. So `must_record` goes to a person or to a
second model, and this file refuses to guess.

    python3 evals/graders/code_check.py <results.json>   # a summary
====================================================================
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals.harness import code_check, is_negative, load_key   # noqa: E402,F401

# The four fields an answer-key row can carry a verdict on, and which
# kind of check owns each. Keep this table; it is the thing the report
# quotes, and burying it in an if-statement makes it unquotable.
CODE_FIELDS = ("decision", "trigger", "missing")
JUDGEMENT_FIELDS = ("must_record",)


def check_kinds(expected):
    """Which kinds of check apply to ONE case.

    Returns {"code": [...], "judgement": [...]} naming the fields, not
    the verdicts. `decision` is always present because every case has an
    expected outcome; the other three appear only when the answer key
    carries them.
    """
    code = ["decision"]                      # every case has one
    if expected.get("trigger"):
        code.append("trigger")               # escalations only
    if expected.get("missing"):
        code.append("missing")               # document/pre-auth requests only

    judgement = []
    if expected.get("must_record"):
        judgement.append("must_record")

    return {"code": code, "judgement": judgement}


def check_kind_label(expected):
    """"code" | "judgement" | "code+judgement" - one string for a table cell."""
    kinds = check_kinds(expected)
    has_code, has_judgement = bool(kinds["code"]), bool(kinds["judgement"])
    if has_code and has_judgement:
        return "code+judgement"
    return "code" if has_code else "judgement"


def grade(record, expected):
    """Run the code check and BUILD the judgement item. Never decide it.

    The judgement block comes back with verdict=None on purpose. This
    function has no opinion about prose and no way to acquire one -
    filling it is evals/graders/judge.py's job, by a person or by a
    second model.
    """
    passed, fails = code_check(record, expected)
    kinds = check_kinds(expected)
    return {
        "case_id": record.get("case_id") or expected.get("case_id"),
        "check_kind": check_kind_label(expected),
        "negative": is_negative(expected),
        "code": {
            "fields": kinds["code"],
            "passed": bool(passed),
            "fails": list(fails),
        },
        "judgement": {
            "fields": kinds["judgement"],
            "required": bool(kinds["judgement"]),
            "items": list(expected.get("must_record") or []),
            "verdict": None,        # <- judge.py fills these two
            "graded_by": None,
        },
    }


# =====================================================================
# A SUMMARY, so the split is visible without opening a results file
# =====================================================================
def main(argv=None):
    argv = argv or sys.argv[1:]
    key = load_key()
    rows = key if isinstance(key, list) else list(key.values())

    counts, items = {}, 0
    for row in rows:
        label = check_kind_label(row)
        counts[label] = counts.get(label, 0) + 1
        items += len(row.get("must_record") or [])

    print()
    print("  WHICH CHECK GRADES WHICH CASE  (D4)")
    print("  " + "-" * 56)
    for label in ("code", "judgement", "code+judgement"):
        if label in counts:
            print("    %-16s %d case(s)" % (label, counts[label]))
    print("    %-16s %d across the set" % ("must_record items", items))
    print()
    print("  Every case carries a code check on `decision`. %d also carry"
          % counts.get("code+judgement", 0))
    print("  prose that only a person or a second model can rule on.")
    print("  Fill those with:  python3 evals/graders/judge.py <results.json>")
    print()

    if argv:
        with open(argv[0], encoding="utf-8") as fh:
            doc = json.load(fh)
        by_id = {r["case_id"]: r for r in rows} if isinstance(rows, list) else key
        seen = set()
        print("  %-12s %-16s %s" % ("case", "check kind", "code check"))
        print("  " + "-" * 56)
        for r in doc.get("results", []):
            cid = r["case_id"]
            if cid in seen:
                continue
            seen.add(cid)
            exp = by_id.get(cid)
            if not exp:
                continue
            print("  %-12s %-16s %s" % (cid, check_kind_label(exp),
                                        "PASS" if r["passed"] else "FAIL"))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
