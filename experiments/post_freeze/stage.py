#!/usr/bin/env python3
"""
PE6201 · A2 — THE POST-FREEZE UPGRADE, STAGED  (D2b, D3a, D3b, D4)
====================================================================
    python3 experiments/post_freeze/stage.py --status   who has run; does the freeze still hold
    python3 experiments/post_freeze/stage.py --check    free, any time: prove the patch
    python3 experiments/post_freeze/stage.py --apply    merge into src/ and evals/ - only
                                                        once --status says every battery is in

WHY A PATCH, AND WHY IT LIVES HERE. Every file the upgrade touches is
hashed into the battery fingerprint (evals/battery_provenance.py
PINNED_SOURCES), and members are still running their batteries. Editing
src/ now would give their runs a different fingerprint from the ones
already committed, and the six-model comparison would stop being one. So
the upgrade is post_freeze.patch, on main, outside src/ and evals/ - it
changes no hash and drifts nobody. `git apply` merges it in one step when
the freeze lifts, and fails loudly, not silently, if src/ has moved.

--check NEVER TOUCHES YOUR WORKING TREE. It clones the committed HEAD
twice into a temporary directory - one clone frozen, one patched - copies
this staging directory in as it is on disk, and checks:

    1  the patch applies cleanly
    2  v1 and v2 prompts hash exactly as the frozen battery recorded; v3 is new
    3  run_eval.py passes every trial, in both trees
    4  the guardrail checklist passes every must-fire and must-not-fire case,
       identically twice
    5  the fake-vendor, judge, cost-model and re-grade suites: 0 failed
    6  D2(c) and both D7 demos print byte-identical output in both trees
    7  the projection over the committed batteries, printed

--apply refuses unless src/ evals/ data/ are clean and every roster member
has a committed battery whose fingerprint matches today's frozen tree, line
endings aside (a Windows checkout hashes CRLF bytes; evals/line_endings.py). It
applies the patch and stops. It does not commit; a person does, on main.
====================================================================
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PATCH = os.path.join(HERE, "post_freeze.patch")

# Stamped into the committed battery results. The patch must not move them.
FROZEN_PROMPTS = {"v1": "36992f7881ec", "v2": "60c5e4344f24"}
COMPARED = ("answer_key_sha256", "fixtures_sha256", "plan_sha256",
            "prompt_sha256", "sources_sha256", "invariants")
# Copied into both clones, so --check runs these files as they are on disk,
# committed or not.
STAGE_FILES = ("experiments/post_freeze", "experiments/regrade_offline.py",
               "experiments/test_regrade_offline.py", "experiments/frozen_graders")

_FP = ("import json, sys; sys.path.insert(0, 'src'); sys.path.insert(0, '.'); "
       "from evals import battery_provenance as bp; fp = bp.fingerprint('A'); "
       "print(json.dumps({k: fp[k] for k in %r}))" % (COMPARED,))


def sh(cmd, cwd, timeout=1200):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout + proc.stderr


def fingerprint(tree):
    code, out = sh([sys.executable, "-c", _FP], cwd=tree)
    if code:
        raise SystemExit("could not fingerprint %s:\n%s" % (tree, out))
    return json.loads(out.strip().splitlines()[-1])


# =====================================================================
# --status
# =====================================================================
def member_status():
    """(member, model, prompt version, matched battery or None, note) per roster row.

    A battery run on a Windows checkout records CRLF-byte hashes for the
    answer key, the fixtures and the pinned sources, although the content is
    today's (evals/line_endings.py). It matches when those fields are today's
    content in either line-ending form and everything else matches exactly.
    """
    frozen = fingerprint(ROOT)
    for p in (ROOT, os.path.join(ROOT, "src")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from evals import line_endings
    forms = line_endings.variants(frozen.get("problem") or "A")
    with open(os.path.join(ROOT, "evals", "battery_roster.json"), encoding="utf-8") as fh:
        roster = json.load(fh)
    rows = []
    for entry in roster.get("members", []):
        member = entry["member"]
        matched = note = None
        for path in sorted(glob.glob(os.path.join(
                ROOT, "results", "live", "battery__%s__*.json" % member))):
            with open(path, encoding="utf-8") as fh:
                fp = json.load(fh).get("fingerprint") or {}
            if all(fp.get(k) == frozen[k] for k in COMPARED):
                matched, note = os.path.relpath(path, ROOT), None
                continue
            same, eols = line_endings.same_content(fp, forms)
            if same and all(fp.get(k) == frozen[k] for k in COMPARED
                            if k not in line_endings.BYTE_HASHED):
                matched = os.path.relpath(path, ROOT)
                note = ("Windows line endings, same content"
                        if "crlf" in eols else None)
        rows.append((member, entry.get("model"), entry.get("prompt_version"), matched, note))
    return rows


def status():
    if os.path.exists(os.path.join(ROOT, "src", "final_check.py")):
        print("\n  The post-freeze patch is already applied to this tree.\n")
        return 0
    rows = member_status()
    print("\n  THE FREEZE - a battery counts only if its fingerprint matches today's tree")
    print("  " + "-" * 92)
    for member, model, version, matched, note in rows:
        print("  %-12s %-34s %-3s %s" % (member, model, version,
                                         matched or "NOT RUN on the frozen fingerprint"))
        if note:
            print("  %-52s ^ %s" % ("", note))
    waiting = [r[0] for r in rows if not r[3]]
    print("  " + "-" * 92)
    if waiting:
        print("  FREEZE HOLDS - still waiting on: %s" % ", ".join(waiting))
        print("  Do not apply the patch. Do not edit src/ or evals/harness.py.\n")
        return 1
    print("  Every battery is in. The freeze can lift:  stage.py --apply\n")
    return 0


# =====================================================================
# --check
# =====================================================================
def _clone(dest):
    code, out = sh(["git", "clone", "--quiet", "--local", "--no-hardlinks", ROOT, dest], cwd=ROOT)
    if code:
        raise SystemExit("git clone failed:\n" + out)
    for rel in STAGE_FILES:
        src, dst = os.path.join(ROOT, rel), os.path.join(dest, rel)
        if os.path.isdir(src):
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        elif os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def _normalise(text, tree):
    text = text.replace(tree, "<tree>")
    return re.sub(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?", "<date>", text)


class Report(object):
    def __init__(self):
        self.rows = []

    def step(self, name, ok, detail=""):
        self.rows.append((name, ok))
        print("  %s  %s%s" % ("PASS" if ok else "FAIL", name,
                              ("\n        " + detail.strip().replace("\n", "\n        ")[:900])
                              if detail and not ok else ""))
        return ok


def check(keep=False):
    rep = Report()
    tmp = tempfile.mkdtemp(prefix="pe6201_post_freeze_")
    frozen, patched = os.path.join(tmp, "frozen"), os.path.join(tmp, "patched")
    print("\n  Staging in %s (your working tree is not touched)\n" % tmp)
    try:
        _clone(frozen)
        _clone(patched)
        code, out = sh(["git", "apply", "--check", PATCH], cwd=patched)
        if not rep.step("1  post_freeze.patch applies cleanly to HEAD", code == 0, out):
            return rep
        sh(["git", "apply", PATCH], cwd=patched)

        fb, fp = fingerprint(frozen), fingerprint(patched)
        rep.step("2  v1 and v2 prompts hash exactly as the frozen battery recorded",
                 all(fp["prompt_sha256"][v].startswith(h) and fb["prompt_sha256"][v].startswith(h)
                     for v, h in FROZEN_PROMPTS.items()),
                 json.dumps({v: fp["prompt_sha256"][v][:12] for v in FROZEN_PROMPTS}))
        rep.step("2a v3 is a new prompt (sha %s)" % (fp["prompt_sha256"].get("v3") or "")[:12],
                 fp["prompt_sha256"].get("v3") not in (None, fp["prompt_sha256"]["v2"]))

        outputs = {}
        for tree, label in ((frozen, "frozen"), (patched, "patched")):
            for name, cmd in (("run_eval", ["run_eval.py"]),
                              ("d2c", ["experiments/d2c_parallel_vs_sequential.py"]),
                              ("d7_loop", ["experiments/demo_loop_failure.py"]),
                              ("d7_tool", ["experiments/demo_tool_interface_failure.py"])):
                code, out = sh([sys.executable] + cmd, cwd=tree)
                outputs[(label, name)] = (code, _normalise(out, tree))
        m = re.search(r"(\d+) of (\d+) trials passed", outputs[("patched", "run_eval")][1])
        rep.step("3  run_eval.py passes every trial on the patched tree",
                 bool(m) and m.group(1) == m.group(2), outputs[("patched", "run_eval")][1][-400:])
        for name, title in (("run_eval", "run_eval.py"), ("d2c", "D2(c) parallel vs sequential"),
                            ("d7_loop", "D7 failure 1 - loop control"),
                            ("d7_tool", "D7 failure 2 - tool interface")):
            same = outputs[("frozen", name)] == outputs[("patched", name)]
            rep.step("6  %s: identical output before and after" % title, same,
                     "" if same else "exit codes %s / %s"
                     % (outputs[("frozen", name)][0], outputs[("patched", name)][0]))

        code, out = sh([sys.executable, "evals/run_guardrails.py", "--twice"], cwd=patched)
        fire = re.search(r"must_fire: (\d+)/(\d+)", out)
        quiet = re.search(r"must_not_fire: (\d+)/(\d+)", out)
        rep.step("4  guardrail checklist: %s must-fire, %s must-not-fire, twice identical"
                 % (fire.group(0).split(": ")[1] if fire else "?",
                    quiet.group(0).split(": ")[1] if quiet else "?"),
                 code == 0 and fire and fire.group(1) == fire.group(2)
                 and quiet and quiet.group(1) == quiet.group(2)
                 and "twice_identical: True" in out, out[-600:])

        for script in ("evals/test_battery_fake.py", "evals/graders/test_judge_fake.py",
                       "experiments/test_regrade_offline.py"):
            code, out = sh([sys.executable, script], cwd=patched)
            counted = re.search(r"(\d+) passed, (\d+) failed", out)
            rep.step("5  %s: %s" % (script, counted.group(0) if counted else "no summary"),
                     code == 0 and counted and counted.group(2) == "0", out[-900:])
        code, out = sh([sys.executable, "evals/test_cost_model.py"], cwd=patched)
        rep.step("5  evals/test_cost_model.py: %s" % out.strip().splitlines()[-1] if out.strip() else "",
                 code == 0 and "passed" in out, out[-400:])

        code, out = sh([sys.executable, "experiments/post_freeze/replay_projection.py"], cwd=patched)
        rep.step("7  projection over the committed batteries", code == 0, out[-600:])
        if code == 0:
            print(out)
    finally:
        if keep:
            print("  Kept: %s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    return rep


# =====================================================================
# --apply
# =====================================================================
def apply():
    if os.path.exists(os.path.join(ROOT, "src", "final_check.py")):
        print("\n  Already applied: src/final_check.py exists.\n")
        return 1
    code, dirty = sh(["git", "status", "--porcelain", "--", "src", "evals", "data"], cwd=ROOT)
    if dirty.strip():
        print("\n  REFUSED - uncommitted changes under src/ evals/ data/:\n%s\n" % dirty)
        return 1
    rows = member_status()
    waiting = [r[0] for r in rows if not r[3]]
    if waiting:
        print("\n  REFUSED - the freeze holds. No battery on the frozen fingerprint for: %s"
              % ", ".join(waiting))
        print("  Applying now would give their runs a different fingerprint from the")
        print("  ones already committed. Run  stage.py --status  to see the table.\n")
        return 1
    code, out = sh(["git", "apply", "--check", PATCH], cwd=ROOT)
    if code:
        print("\n  REFUSED - the patch no longer applies cleanly:\n%s\n" % out)
        return 1
    code, out = sh(["git", "apply", PATCH], cwd=ROOT)
    if code:
        print("\n  git apply failed:\n%s\n" % out)
        return 1
    print("\n  Applied to src/ and evals/. Nothing is committed yet. Next, on main:")
    print("    python3 run_eval.py && python3 evals/run_guardrails.py --twice")
    print("    python3 evals/test_battery_fake.py && python3 experiments/test_regrade_offline.py")
    print("    then update the documents listed in experiments/post_freeze/README.md,")
    print("    commit, and set prompt_version \"v3\" for any member who re-runs.\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stage.py")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--keep", action="store_true", help="--check: keep the clones")
    args = ap.parse_args(argv)
    if args.status:
        return status()
    if args.apply:
        return apply()
    rep = check(keep=args.keep)
    failed = [name for name, ok in rep.rows if not ok]
    print("  " + "=" * 72)
    print("  %d passed, %d failed" % (len(rep.rows) - len(failed), len(failed)))
    print("  " + "=" * 72 + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
