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

WHICH GRADER. Every run is re-scored with THE HARNESS IT WAS GRADED WITH,
identified by the evals/harness.py hash in its own fingerprint - not with
whatever evals/harness.py says today. Once the post-freeze patch moves
both fixes into harness.py, "today's harness" already contains them, and a
re-grade against it would quietly apply each fix twice and call the
result a baseline. The run's grader is loaded from a byte-identical copy
under experiments/frozen_graders/ (hash-checked before use, so it works
from a copy of the repository with no .git), else from git history at the
run's commit, else today's harness - and the row says which.
====================================================================
"""
import argparse
import glob
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

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
FROZEN_GRADERS = os.path.join(ROOT, "experiments", "frozen_graders")
GATED = "issue_decision_letter"

VARIANTS = (
    ("recorded", "as recorded"),
    ("rescored", "re-scored, own harness"),
    ("underscore", "+ underscore fix"),
    ("letter_rule", "+ letter rule"),
    ("both", "both fixes"),
)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# =====================================================================
# THE RUN'S OWN GRADER
# =====================================================================
_GRADERS = {}


def _load_module(path, sha):
    spec = importlib.util.spec_from_file_location("harness_%s" % sha[:12], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_grader(sha, commit=None):
    """(module, how) - evals/harness.py exactly as a run was graded by it."""
    if (sha, commit) in _GRADERS:
        return _GRADERS[(sha, commit)]
    found = None
    vendored = os.path.join(FROZEN_GRADERS, "harness_%s.py" % (sha or "")[:12])
    if sha and os.path.exists(vendored) and sha256_file(vendored) == sha:
        found = (_load_module(vendored, sha), "harness %s (vendored copy)" % sha[:12])
    elif sha and commit:
        shown = subprocess.run(["git", "-C", ROOT, "show", "%s:evals/harness.py" % commit],
                               capture_output=True)
        if (shown.returncode == 0
                and hashlib.sha256(shown.stdout).hexdigest() == sha):
            tmp = os.path.join(tempfile.mkdtemp(), "harness.py")
            with open(tmp, "wb") as fh:
                fh.write(shown.stdout)
            found = (_load_module(tmp, sha), "harness %s (git %s)" % (sha[:12], commit[:12]))
    if found is None:
        found = (harness, "TODAY'S harness - the run's own was not found")
    _GRADERS[(sha, commit)] = found
    return found


def grader_for(doc):
    fp = doc.get("fingerprint") or {}
    return load_grader((fp.get("sources_sha256") or {}).get("evals/harness.py"),
                       doc.get("commit") or fp.get("commit"))


# =====================================================================
# FIX 1 · UNDERSCORES
# =====================================================================
def normalise(value):
    """Formatting only. `None` stays None so "nothing was named" still fails."""
    return None if value is None else str(value).replace("_", " ")


def code_check(record, expected, underscore=False, grader=None):
    """A harness's code_check, optionally on a normalised copy.

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
    return (grader or harness).code_check(record, expected)


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
    grader, graded_with = grader_for(doc)
    by_variant = {name: [] for name, _ in VARIANTS}
    changes, unkeyed = [], []

    for r in doc.get("results", []):
        case_id, rec = r["case_id"], r.get("record") or {}
        expected = key.get(case_id)
        if expected is None:
            unkeyed.append(case_id)
            continue

        base_ok, base_fails = code_check(rec, expected, grader=grader)
        us_ok, us_fails = code_check(rec, expected, underscore=True, grader=grader)
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
        "graded_with": graded_with,
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
    w("  OFFLINE RE-GRADE - %d battery file(s), answer key %s"
      % (len(result["runs"]), result["answer_key_sha256"][:12]))
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
        w("  %-44s graded with %s" % ("", run["graded_with"]))
        if not run["rescored_matches_recorded"]:
            w("  %-44s ! that harness disagrees with %d recorded grade(s)"
              % ("", sum(1 for c in run["changes"] if c["fix"] == "rescored")))
        if run["unkeyed_cases"]:
            w("  %-44s ! not in today's answer key, skipped: %s"
              % ("", ", ".join(run["unkeyed_cases"])))
    w("")
    w("  'as recorded' is the battery file's own grade. Every other row uses the")
    w("  harness that graded that run, identified by hash; the two fixes are")
    w("  applied on top of it, alone and together. Archived runs have no ledger,")
    w("  so their letter-rule row is approximate.")
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
        "- Answer key `%s` · each run re-scored with the `evals/harness.py` "
        "that graded it, identified by hash" % result["answer_key_sha256"][:12],
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
