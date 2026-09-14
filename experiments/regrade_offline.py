#!/usr/bin/env python3
"""
PE6201 · A2 — OFFLINE RE-GRADE: TWO GRADER FIXES, EVERY BATTERY  (D4, D5b)
====================================================================
    python3 experiments/regrade_offline.py            # the pass-rate matrix
    python3 experiments/regrade_offline.py --trials   # ...and every trial that moved
    python3 experiments/regrade_offline.py --write    # ...and results/regrade/

Free, offline, deterministic. Reads the committed battery files and the
decision ledgers their runs wrote. Changes none of them.

WHY THIS IS A SCRIPT AND NOT AN EDIT TO evals/harness.py. harness.py is in
battery_provenance.PINNED_SOURCES. Four members have not run yet; editing
it now would give their batteries a different fingerprint from the two
already committed, and the six-model comparison would stop being one.
So the fixes live here, run against the frozen harness, and move into
harness.py only once every battery has landed (experiments/post_freeze/).

TWO FIXES, BOTH DECLARED IN THE REPORT, BOTH APPLIED TO EVERY RUN ALIKE.

  1 · UNDERSCORES ARE SPACES when a named missing item is compared.
      check_coverage returns `required_document: "itemised_bill"`. A model
      that repeats the tool's own identifier back - "itemised_bill for
      code 45378" - named the right document on the right line, and
      _missing_matches failed it for spelling the document the way our
      own tool spells it. The fix normalises formatting, not meaning:
      the line code, the date and the pre-authorisation/document split
      are still compared exactly, and a wrong document still fails.

  2 · AN APPROVAL MUST ACTUALLY SEND ITS LETTER. The brief's D4 code check
      is "whether the gated action fired exactly once"; the FAQ's is
      "exactly once or not at all"; docs/D0c_what_good_looks_like.md says
      "exactly once, or not at all when the run escalates". An approval
      is the ACT outcome - if no letter went out, nothing was approved.
      harness.code_check only enforced "at most once", so an
      approve_in_principle that never sent its letter passed.

      "Sent" is read from the ledger, never from the call list. The loop
      appends a call to `evidence` even when the tool BLOCKED it, so a
      name in `evidence` proves an attempt, not a send. A ledger row is
      written only on success. Each row is matched to exactly one trial
      by case id and by the run's token counts at the moment of the call,
      which is what the loop stamps on the row - so the scripted preflight
      and the live canary, which share the ledger file, cannot stand in
      for a battery trial.

      Runs with no ledger (the archived ones) fall back to `gate_passed`
      and are labelled APPROXIMATE wherever they are printed.
====================================================================
"""
import argparse
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals import harness                                  # noqa: E402
from evals.run_battery import aggregate                    # noqa: E402

LIVE = os.path.join(ROOT, "results", "live", "battery__*.json")
ARCHIVE = os.path.join(ROOT, "results", "archive", "live", "battery__*.json")
LEDGER_DIR = os.path.join(ROOT, "logs", "battery")
OUT_DIR = os.path.join(ROOT, "results", "regrade")
KEY_PATH = os.path.join(ROOT, "data", "expected_outcomes_A.json")
GATED = "issue_decision_letter"

VARIANTS = (
    ("recorded", "as recorded"),
    ("rescored", "re-scored, frozen harness"),
    ("underscore", "+ underscore fix"),
    ("letter_rule", "+ letter rule"),
    ("both", "both fixes"),
)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# =====================================================================
# FIX 1 · UNDERSCORES
# =====================================================================
def normalise(value):
    """Formatting only. `None` stays None so "nothing was named" still fails."""
    return None if value is None else str(value).replace("_", " ")


def code_check(record, expected, underscore=False):
    """The frozen harness.code_check, optionally on a normalised copy.

    Only the `missing` field is normalised, on both sides. The decision,
    the trigger and the gated-action count are compared exactly as the
    battery compared them.
    """
    if underscore:
        record, expected = dict(record), dict(expected)
        if record.get("missing") is not None:
            record["missing"] = normalise(record["missing"])
        if expected.get("missing"):
            expected["missing"] = normalise(expected["missing"])
    return harness.code_check(record, expected)


# =====================================================================
# FIX 2 · THE LETTER WAS SENT
# =====================================================================
def running_totals(record):
    """(tokens_in, tokens_out) after each model call, in call order.

    loop_agent stamps the gated call's ledger row with exactly these
    running totals, so they identify which trial wrote the row.
    """
    tin = tout = 0
    totals = []
    for pair in record.get("turn_tokens") or []:
        tin, tout = tin + pair[0], tout + pair[1]
        totals.append((tin, tout))
    return totals


def ledger_path(doc):
    return os.path.join(LEDGER_DIR, "decisions__%s__%s.jsonl"
                        % (doc.get("member"), doc.get("run_id")))


class Ledger(object):
    """The rows a run's gated action wrote, each claimable by ONE trial."""

    def __init__(self, rows, backend):
        # The scripted preflight writes into the same file before a live
        # battery starts. Its rows are not evidence about the live model.
        self.rows = [r for r in rows if r.get("backend") == backend]
        self.used = set()

    @classmethod
    def for_run(cls, doc):
        path = ledger_path(doc)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        return cls(rows, doc.get("backend"))

    def claim(self, case_id, record):
        totals = set(running_totals(record))
        for i, row in enumerate(self.rows):
            if i in self.used or row.get("case_id") != case_id:
                continue
            if (row.get("tokens_in"), row.get("tokens_out")) in totals:
                self.used.add(i)
                return row
        return None


def _gate_passed(record):
    for g in record.get("guardrails_fired") or []:
        name = g.get("guardrail") if isinstance(g, dict) else g
        if name == "gate_passed":
            return True
    return False


def letter_sent(record, case_id, ledger):
    """(sent, how) for an approve_in_principle record."""
    if GATED not in (record.get("evidence") or []):
        return False, "%s was never called" % GATED
    if ledger is None:
        return _gate_passed(record), "APPROXIMATE - no ledger, gate_passed used"
    row = ledger.claim(case_id, record)
    if row is None:
        return False, "%s was called but no sent row matches this trial" % GATED
    if row.get("decision") != "approve_in_principle":
        return False, "the letter sent was a %r, not the approval" % row.get("decision")
    return True, "ledger row matched"


# =====================================================================
# ONE RUN
# =====================================================================
def regrade_run(doc, key):
    ledger = Ledger.for_run(doc)
    by_variant = {name: [] for name, _ in VARIANTS}
    changes, unkeyed = [], []

    for r in doc.get("results", []):
        case_id, rec = r["case_id"], r.get("record") or {}
        expected = key.get(case_id)
        if expected is None:
            unkeyed.append(case_id)
            continue

        base_ok, base_fails = code_check(rec, expected)
        us_ok, us_fails = code_check(rec, expected, underscore=True)
        letter_fail = None
        if rec.get("decision") == "approve_in_principle":
            sent, how = letter_sent(rec, case_id, ledger)
            if not sent:
                letter_fail = "approve_in_principle without a sent letter (%s)" % how

        verdicts = {
            "recorded": bool(r.get("passed")),
            "rescored": base_ok,
            "underscore": us_ok,
            "letter_rule": base_ok and letter_fail is None,
            "both": us_ok and letter_fail is None,
        }
        for name, passed in verdicts.items():
            by_variant[name].append({"case_id": case_id, "trial": r.get("trial"),
                                     "passed": passed, "record": rec})

        why = {
            "underscore": "; ".join(base_fails) if us_ok else "",
            "letter_rule": letter_fail or "",
        }
        for name in ("rescored", "underscore", "letter_rule"):
            before = verdicts["recorded"] if name == "rescored" else verdicts["rescored"]
            if verdicts[name] != before:
                changes.append({"case_id": case_id, "trial": r.get("trial"),
                                "fix": name, "from": before, "to": verdicts[name],
                                "why": why.get(name) or "frozen harness disagrees "
                                                        "with the recorded grade"})

    summaries = {}
    for name, _ in VARIANTS:
        s = aggregate(by_variant[name], key) if by_variant[name] else None
        if s:
            summaries[name] = {k: s[k] for k in ("trials_graded", "passed", "pass_rate",
                                                 "ordinary", "negative")}
    return {
        "member": doc.get("member"),
        "model": doc.get("model"),
        "prompt_version": doc.get("prompt_version"),
        "run_id": doc.get("run_id"),
        "date": doc.get("date"),
        "started": doc.get("started"),
        "answer_key_sha256": (doc.get("fingerprint") or {}).get("answer_key_sha256"),
        "ledger": (os.path.relpath(ledger_path(doc), ROOT) if ledger is not None else None),
        "letter_rule_exact": ledger is not None,
        "rescored_matches_recorded": not any(c["fix"] == "rescored" for c in changes),
        "unkeyed_cases": sorted(set(unkeyed)),
        "summaries": summaries,
        "changes": changes,
    }


def discover():
    found = []
    for pattern, archived in ((LIVE, False), (ARCHIVE, True)):
        for path in sorted(glob.glob(pattern)):
            found.append((path, archived))
    return found


def regrade_all(paths=None):
    key = harness.load_key("A")
    runs = []
    for path, archived in (paths if paths is not None else discover()):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        run = regrade_run(doc, key)
        run["archived"] = archived
        run["file"] = os.path.relpath(path, ROOT)
        runs.append(run)
    runs.sort(key=lambda x: (x["archived"], x["started"] or "", x["run_id"] or ""))
    return {
        "answer_key_sha256": sha256_file(KEY_PATH),
        "harness_sha256": sha256_file(os.path.join(ROOT, "evals", "harness.py")),
        "fixes": {
            "underscore": "missing-item comparison treats '_' as ' ' on both sides",
            "letter_rule": "an approve_in_principle fails unless a ledger row shows "
                           "its decision letter was sent (brief D4: gated action "
                           "fired exactly once)",
        },
        "runs": runs,
    }


# =====================================================================
# RENDERING
# =====================================================================
def _frac(n, d):
    return "%d/%d %5.1f%%" % (n, d, 100.0 * n / d) if d else "-"


def _cells(s):
    o, n = s["ordinary"], s["negative"]
    return (_frac(s["passed"], s["trials_graded"]),
            _frac(round(o["rate"] * o["trials"]), o["trials"]),
            _frac(round(n["rate"] * n["trials"]), n["trials"]),
            "%d/%d" % (n["cases_3of3"], n["cases"]) if n["cases"] else "-")


def render(result, show_trials=False):
    out = []
    w = out.append
    w("=" * 104)
    w("  OFFLINE RE-GRADE - %d battery file(s), answer key %s, frozen harness %s"
      % (len(result["runs"]), result["answer_key_sha256"][:12],
         result["harness_sha256"][:12]))
    w("=" * 104)
    w("  %-44s %-26s %-14s %-15s %-15s %s"
      % ("run", "grader", "all trials", "ordinary", "negative", "neg 3/3"))
    for run in result["runs"]:
        w("  " + "-" * 102)
        label = "%s · %s · %s" % (run["member"], run["model"], run["prompt_version"])
        tag = "%s%s" % (run["run_id"], "  ARCHIVED" if run["archived"] else "")
        for i, (name, title) in enumerate(VARIANTS):
            s = run["summaries"].get(name)
            if not s:
                continue
            if name == "letter_rule" and not run["letter_rule_exact"]:
                title += " (approx)"
            first = label[:44] if i == 0 else (tag if i == 1 else "")
            w("  %-44s %-26s %-14s %-15s %-15s %s" % ((first, title) + _cells(s)))
        if not run["rescored_matches_recorded"]:
            w("  %-44s ! the frozen harness disagrees with %d recorded grade(s)"
              % ("", sum(1 for c in run["changes"] if c["fix"] == "rescored")))
        if run["unkeyed_cases"]:
            w("  %-44s ! not in today's answer key, skipped: %s"
              % ("", ", ".join(run["unkeyed_cases"])))
    w("")
    w("  'as recorded' is the battery file's own grade. Every other row is the")
    w("  frozen evals/harness.py; the two fixes are applied on top of it, alone")
    w("  and together. Archived runs were measured on harness versions since")
    w("  fixed and have no ledger - their letter-rule row is approximate.")
    w("")
    if show_trials:
        w("  TRIALS WHOSE GRADE MOVED")
        for run in result["runs"]:
            moved = [c for c in run["changes"] if c["fix"] != "rescored"]
            if not moved:
                continue
            w("  %s · %s · %s" % (run["member"], run["model"], run["run_id"]))
            for c in moved:
                w("    %-9s t%-2s %-12s %s -> %s  %s"
                  % (c["case_id"], c["trial"], c["fix"],
                     "PASS" if c["from"] else "FAIL", "PASS" if c["to"] else "FAIL",
                     c["why"][:60]))
        w("")
    return "\n".join(out)


def render_markdown(result):
    lines = [
        "# Offline re-grade — two grader fixes, every battery",
        "",
        "Generated by `python3 experiments/regrade_offline.py --write`. Free, offline,",
        "deterministic. The battery files are unchanged; this is a second grading of",
        "the same records.",
        "",
        "- Answer key `%s` · frozen `evals/harness.py` `%s`"
        % (result["answer_key_sha256"][:12], result["harness_sha256"][:12]),
        "- **Underscore fix:** %s." % result["fixes"]["underscore"],
        "- **Letter rule:** %s." % result["fixes"]["letter_rule"],
        "",
        "| Run | Grader | All trials | Ordinary | Negative | Negative 3/3 |",
        "|---|---|---|---|---|---|",
    ]
    for run in result["runs"]:
        label = "%s · `%s` · %s · `%s`%s" % (
            run["member"], run["model"], run["prompt_version"], run["run_id"],
            " · archived" if run["archived"] else "")
        for i, (name, title) in enumerate(VARIANTS):
            s = run["summaries"].get(name)
            if not s:
                continue
            if name == "letter_rule" and not run["letter_rule_exact"]:
                title += " (approximate)"
            lines.append("| %s | %s | %s | %s | %s | %s |"
                         % ((label if i == 0 else "", title) + _cells(s)))
    lines += ["", "## Trials whose grade moved", ""]
    for run in result["runs"]:
        moved = [c for c in run["changes"] if c["fix"] != "rescored"]
        if not moved:
            continue
        lines.append("**%s · `%s` · `%s`**" % (run["member"], run["model"], run["run_id"]))
        lines.append("")
        for c in moved:
            lines.append("- %s trial %s — %s: %s → %s. %s"
                         % (c["case_id"], c["trial"], c["fix"],
                            "pass" if c["from"] else "fail",
                            "pass" if c["to"] else "fail", c["why"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write(result):
    os.makedirs(OUT_DIR, exist_ok=True)
    json_path = os.path.join(OUT_DIR, "regrade_matrix.json")
    md_path = os.path.join(OUT_DIR, "regrade_matrix.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(result))
    return json_path, md_path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="regrade_offline.py")
    ap.add_argument("--trials", action="store_true",
                    help="list every trial whose grade moved, and why")
    ap.add_argument("--write", action="store_true",
                    help="write results/regrade/regrade_matrix.{json,md}")
    args = ap.parse_args(argv)
    result = regrade_all()
    if not result["runs"]:
        print("\n  No battery files under results/live/ or results/archive/live/.\n")
        return 1
    print()
    print(render(result, show_trials=args.trials))
    if args.write:
        for path in write(result):
            print("  Wrote %s" % os.path.relpath(path, ROOT))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
