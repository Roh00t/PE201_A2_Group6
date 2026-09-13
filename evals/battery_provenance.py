"""
PE6201 · A2 — BATTERY PROVENANCE  (D5b)
====================================================================
Pure functions. No network, no spend, no side effects. Imported by the
runner, the aggregator and the fake-vendor test alike.

WHAT PROBLEM THIS SOLVES. Six members run the same evaluation set on
six models and the numbers get compared in one table. The brief is
blunt about the risk: "with three runners drift is survivable; with six
it silently voids the whole battery." SILENTLY is the word that matters.
Nothing about a drifted run looks wrong - it produces a pass rate, in
the right format, at the right cost, that simply is not comparable with
anyone else's. Nobody gets an error message.

So every component that must be identical across the six is hashed, the
hashes travel in the results file, and a mismatch REFUSES and names the
component that moved. "The answer key differs" is actionable;
"fingerprint mismatch" is not.

WHAT IS DELIBERATELY NOT IN THE FINGERPRINT. The model, the prompt
version, the prices and the key. Those are the variables and the secret
- fingerprinting them would make every member's run "drift" from every
other by construction.
====================================================================
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config                                        # noqa: E402
import prompt                                        # noqa: E402
from evals import harness                            # noqa: E402

ROSTER_PATH = os.path.join(ROOT, "evals", "battery_roster.json")

# Files whose bytes must be identical across all six runs. Outputs are
# deliberately excluded: logs/ and results/ change BECAUSE you ran, and
# a dirty check that trips on your own output is a check nobody obeys.
# Every prompt version that can appear in the roster. v2_scaffolded was
# removed on 2026-09-13: it was an experiment on a loop that could not see
# its own calls and never told the model which claim to decide. Both are
# fixed, and its useful parts now live in v2's process section.
PROMPT_VERSIONS = ("v1", "v2")

PINNED_SOURCES = [
    "src/config.py",
    "src/prompt.py",
    "src/tools/tools.py",
    "src/backends/backends.py",
    "src/backends/planner.py",
    "src/backends/guardrails.py",
    "src/loop_agent.py",
    "src/narrative_guard.py",
    "evals/harness.py",
]
DIRTY_CHECK_PATHS = ["src", "evals", "data"]


# =====================================================================
# HASHING
# =====================================================================
def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(obj):
    return sha256_text(json.dumps(obj, sort_keys=True, separators=(",", ":")))


def short(digest):
    return digest[:12] if digest else "-"


# =====================================================================
# GIT
# =====================================================================
def _git(*args):
    try:
        return subprocess.run(["git"] + list(args), cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def git_head_sha():
    return _git("rev-parse", "HEAD")


def resolve_tag(tag):
    """A tag name resolved to a SHA at RUNTIME.

    The roster cannot contain the SHA of the commit that contains the
    roster - that is a chicken-and-egg the tag sidesteps.
    """
    return _git("rev-list", "-n", "1", tag) if tag else ""


def git_dirty(paths=None):
    """Modified/untracked files under the paths that must not move.

    Scoped on purpose. `logs/` and `results/` are outputs; including them
    would mean the second member's run refuses because the first member's
    run wrote a file.
    """
    out = _git("status", "--porcelain", "--", *(paths or DIRTY_CHECK_PATHS))
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def git_diff_stat(paths=None):
    return _git("diff", "--stat", "--", *(paths or DIRTY_CHECK_PATHS))


# =====================================================================
# THE PLAN — one definition of "which trials, in what order"
# =====================================================================
def build_plan(problem=None):
    """The ordered [(case_id, trial), ...] the battery will run.

    Derived from harness.load_cases + load_key + harness.is_negative, so
    the 1-vs-3 trial policy has exactly ONE definition in this repository.
    Hashing this catches three things a hash of the answer key alone
    would miss: a case added to claims.json with no label (run_set only
    prints "SKIP" and carries on), a case removed, and a label flipping
    between ordinary and negative - which silently changes the trial
    count without changing the number of cases.
    """
    problem = problem or config.PROBLEM
    key = harness.load_key(problem)
    plan = []
    for cid in harness.load_cases(problem):
        expected = key.get(cid)
        if expected is None:
            continue
        for trial in range(1, (3 if harness.is_negative(expected) else 1) + 1):
            plan.append((cid, trial))
    return plan


def plan_shape(problem=None):
    """Counts, DERIVED. Never write 60 down anywhere - a number that is
    computed cannot silently disagree with the fixtures, and a number
    that is typed eventually will."""
    problem = problem or config.PROBLEM
    key = harness.load_key(problem)
    cases = [c for c in harness.load_cases(problem) if c in key]
    negative = [c for c in cases if harness.is_negative(key[c])]
    return {"cases": len(cases),
            "negative": len(negative),
            "ordinary": len(cases) - len(negative),
            "trials": len(cases) - len(negative) + 3 * len(negative)}


def assembled_prompt(problem=None, version=None):
    """The exact bytes that go into the system message for a version."""
    return prompt.build_system_prompt(problem or config.PROBLEM, version)


# =====================================================================
# THE FINGERPRINT
# =====================================================================
def fingerprint(problem=None):
    problem = problem or config.PROBLEM
    plan = build_plan(problem)
    key_path = os.path.join(config.data_root(),
                            "expected_outcomes_%s.json" % problem)
    fixtures = sorted(os.listdir(os.path.join(config.data_root(),
                                              "data_%s" % problem)))
    return {
        "problem": problem,
        "commit": git_head_sha(),
        "dirty": git_dirty(),
        "answer_key_sha256": sha256_file(key_path),
        "fixtures_sha256": sha256_json(
            {f: sha256_file(os.path.join(config.data_root(),
                                         "data_%s" % problem, f))
             for f in fixtures if f.endswith(".json")}),
        "plan_sha256": sha256_json(plan),
        "plan_shape": plan_shape(problem),
        "prompt_sha256": {v: sha256_text(assembled_prompt(problem, v))
                          for v in PROMPT_VERSIONS},
        "sources_sha256": {p: sha256_file(os.path.join(ROOT, p))
                           for p in PINNED_SOURCES},
        "invariants": {
            "PROBLEM": config.PROBLEM,
            "GROUPING": config.GROUPING,
            "MAX_TURNS": config.MAX_TURNS,
            "MAX_TOKENS_PER_RUN": config.MAX_TOKENS_PER_RUN,
            "MAX_TOKENS_PER_CALL": config.MAX_TOKENS_PER_CALL,
            "AUTONOMY": config.AUTONOMY,
            "TEMPERATURE": config.TEMPERATURE,
            "BASE_URL": config.BASE_URL,
        },
        "python": "%d.%d.%d" % sys.version_info[:3],
    }


def run_id(fp, entry):
    """Identity of THIS member's run of THIS experiment.

    Includes the fingerprint, so a changed experiment yields a different
    run_id and therefore a different checkpoint file. Resume-safety falls
    out of drift-safety for free: you cannot accidentally resume half a
    battery from before an edit onto half a battery from after it.
    """
    stable = {k: v for k, v in fp.items() if k != "dirty"}
    return sha256_json([stable, entry["member"], entry["model"],
                        entry["prompt_version"]])[:12]


class Violation(object):
    def __init__(self, check, expected, actual, fatal=True, hint=""):
        self.check, self.expected, self.actual = check, expected, actual
        self.fatal, self.hint = fatal, hint

    def __str__(self):
        return ("  %-22s %s\n      expected %s\n      actual   %s%s"
                % (self.check, "FATAL" if self.fatal else "warning",
                   self.expected, self.actual,
                   "\n      -> %s" % self.hint if self.hint else ""))


# Checks that may never be overridden. These are not "your run measures
# something slightly different" - they are "your run measures nothing".
UNOVERRIDABLE = {"prompt_v1_vs_v2", "v1_descriptors_missing",
                 "backend_is_live", "roster_structure", "trials_derived"}


def check_drift(fp, roster, entry):
    """Every reason this run would not be comparable with the others."""
    v = []
    exp = roster.get("expected", {})

    want_commit = resolve_tag(roster.get("battery_tag", ""))
    if want_commit and fp["commit"] != want_commit:
        v.append(Violation("commit", short(want_commit), short(fp["commit"]),
                           hint="git checkout %s" % roster.get("battery_tag")))
    if fp["dirty"]:
        v.append(Violation("worktree_clean", "no changes under %s"
                           % "/ ".join(DIRTY_CHECK_PATHS),
                           "%d changed file(s)" % len(fp["dirty"]),
                           hint="commit or stash them, or pass --allow-dirty"))

    for name in ("answer_key_sha256", "plan_sha256", "fixtures_sha256"):
        if exp.get(name) and exp[name] != fp[name]:
            v.append(Violation(name, short(exp[name]), short(fp[name]),
                               hint="the evaluation set is not the one the "
                                    "others ran"))

    for src, want in (exp.get("sources_sha256") or {}).items():
        got = fp["sources_sha256"].get(src)
        if got != want:
            v.append(Violation("source:" + src, short(want), short(got)))

    # --- the v1/v2 checks. These are why member 6's run means anything.
    ver = entry["prompt_version"]
    want_prompt = (exp.get("prompt_sha256") or {}).get(ver)
    if want_prompt and want_prompt != fp["prompt_sha256"][ver]:
        v.append(Violation("prompt_" + ver, short(want_prompt),
                           short(fp["prompt_sha256"][ver])))
    if fp["prompt_sha256"]["v1"] == fp["prompt_sha256"]["v2"]:
        v.append(Violation(
            "prompt_v1_vs_v2", "v1 and v2 differ", "they are IDENTICAL",
            hint="tools.DESCRIPTORS_V1 is empty or equals DESCRIPTORS. A v1 "
                 "battery against a v2 prompt is a confident wrong number, "
                 "not a missing one."))
    if ver == "v1":
        from tools import tools as _t
        missing = [n for n in sorted(_t.REGISTRY[fp["problem"]])
                   if n not in _t.DESCRIPTORS_V1]
        if missing:
            v.append(Violation(
                "v1_descriptors_missing", "a v1 descriptor for every tool",
                "missing: %s" % ", ".join(missing),
                hint="Huang Yu owns DESCRIPTORS_V1 in src/tools/tools.py"))

    for name, want in (roster.get("invariants") or {}).items():
        got = fp["invariants"].get(name)
        if got != want:
            v.append(Violation("invariant:" + name, repr(want), repr(got)))

    declared = roster.get("trials_expected")
    if declared is not None and declared != fp["plan_shape"]["trials"]:
        v.append(Violation(
            "trials_derived", "%s (roster)" % declared,
            "%d (derived from the fixtures)" % fp["plan_shape"]["trials"],
            hint="the roster and the data disagree about the size of the "
                 "experiment; fix the roster, never the derivation"))
    return v


# =====================================================================
# THE ROSTER
# =====================================================================
def load_roster(path=None):
    with open(path or ROSTER_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def validate_roster(roster, today=None):
    """The brief's two conditions, as code rather than as a checklist.

    "Your models must span at least two price tiers, and no two members
    may take models from the same family." Six busy people will not
    reliably remember that at 11pm the night before a deadline, so it is
    checked here - before getpass, before a single dollar moves.
    """
    errs = []
    members = roster.get("members") or []
    if len(members) < 3:
        errs.append("at least 3 members required; found %d" % len(members))

    names = [m.get("member") for m in members]
    if len(set(names)) != len(names):
        errs.append("duplicate member keys: %s" % names)

    v2 = [m for m in members if m.get("prompt_version") == "v2"]
    v1 = [m for m in members if m.get("prompt_version") == "v1"]

    if len(v1) != 1:
        errs.append("exactly one member must run v1 (the D2(b) pass); found %d"
                    % len(v1))
    if len(v2) < 3:
        errs.append("three live models is the floor that passes; found %d"
                    % len(v2))

    fams = [m.get("family") for m in v2]
    if len(set(fams)) != len(fams):
        errs.append("two v2 members share a model family (%s). Six mid-tier "
                    "models from two vendors is not a comparison." % fams)
    if len(set(m.get("tier") for m in v2)) < 2:
        errs.append("v2 models must span at least two price tiers; found only "
                    "%s" % sorted(set(m.get("tier") for m in v2)))

    if v1 and v2 and v1[0].get("model") not in [m.get("model") for m in v2]:
        errs.append("the v1 member's model (%s) is not one any v2 member ran. "
                    "Comparing prompt versions means holding the MODEL fixed; "
                    "otherwise it isolates two variables, not one."
                    % v1[0].get("model"))

    # A PROMPT VERSION THAT NO LONGER EXISTS. v2_scaffolded was removed on
    # 2026-09-13 while a roster row still named it; without this check the
    # row validated cleanly and would have failed only at the preflight
    # banner, after the member had typed their model id.
    for m in members:
        if m.get("prompt_version") and m.get("prompt_version") not in PROMPT_VERSIONS:
            errs.append("%s: prompt_version %r is not one of %s"
                        % (m.get("member"), m.get("prompt_version"),
                           list(PROMPT_VERSIONS)))

    today = today or datetime.date.today()
    for m in members:
        for field in ("member", "model", "family", "tier", "prompt_version"):
            if not m.get(field):
                errs.append("%s: missing %s" % (m.get("member", "?"), field))
        if str(m.get("model", "")).startswith("<"):
            errs.append("%s: model is still a placeholder (%r)"
                        % (m.get("member"), m.get("model")))
        checked = m.get("price_checked_on")
        if not checked:
            errs.append("%s: price_checked_on is missing - a price you did "
                        "not verify is not a measurement" % m.get("member"))
        else:
            try:
                age = (today - datetime.date.fromisoformat(checked)).days
                if age > 14:
                    errs.append("%s: price last checked %d days ago (%s). "
                                "Verify on the day and record the date."
                                % (m.get("member"), age, checked))
            except ValueError:
                errs.append("%s: price_checked_on %r is not a date"
                            % (m.get("member"), checked))
    return errs


def member_entry(roster, name):
    for m in roster.get("members", []):
        if m.get("member", "").lower() == str(name).lower():
            return m
    raise SystemExit(
        "\n  No member %r in the roster.\n  Known members: %s\n"
        % (name, ", ".join(m.get("member", "?")
                           for m in roster.get("members", []))))
