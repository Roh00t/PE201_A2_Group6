#!/usr/bin/env python3
"""
PE6201 · A2 — REHEARSE complete_judgement.py WITHOUT A KEY OR A DOLLAR
====================================================================
    python3 experiments/test_complete_judgement.py

Free and offline. Copies li_yunke's committed battery (run e7dd3797c778)
into a temporary folder, then recreates her first judging pass the way
run_live_battery.py ran it: judge.main on her member copy, with a fake
judge. Her battery file still carries the 18-case queue that pass judged.
Then it runs the completion against that folder.

The real results/ tree is never written. The fake judge replaces
judge.LIVE_CALL, the same seam test_judge_fake.py uses.
====================================================================
"""
import builtins
import glob
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments"))

import config                                              # noqa: E402
import complete_judgement as cj                            # noqa: E402
from backends.backends import LiveFatalError               # noqa: E402
from evals import harness                                  # noqa: E402
from evals import run_battery as rb                        # noqa: E402
from evals.graders import judge                            # noqa: E402

RUN_ID = "e7dd3797c778"
MEMBER = "li_yunke"
FAKE_KEY = "sk-or-FAKE-complete-judgement-never-leaves-memory"
COST_PER_CALL = 0.0004

PASSED, FAILED = [], []


def check(label, condition, detail=""):
    (PASSED if condition else FAILED).append(label)
    print("  %s  %s%s" % ("PASS" if condition else "FAIL", label,
                          "" if condition else "   <- %s" % detail))


def items_from_prompt(system_message):
    """The REQUIRED ITEMS array, read back out of the rendered judge prompt."""
    tail = system_message.split("REQUIRED ITEMS", 1)[1]
    blob = tail[tail.index("```json") + len("```json"):]
    return json.loads(blob[:blob.index("```")].strip())


def fake_judge(messages, n):
    items = items_from_prompt(messages[0]["content"])
    verdicts = [{"item": it, "verdict": "absent" if (n % 4 == 0 and i == 0)
                 else "present", "evidence": "fake"}
                for i, it in enumerate(items)]
    return (json.dumps({"items": verdicts, "reason": "fake"}),
            {"prompt_tokens": 1000, "completion_tokens": 100,
             "cost": COST_PER_CALL},
            {"served_model": "fake/judge"})


def failing_after(good_calls):
    def fake(messages, n):
        if n > good_calls:
            raise LiveFatalError("HTTP 402 - out of credit")
        return fake_judge(messages, n)
    return fake


def snapshot(root):
    out = {}
    for path in sorted(glob.glob(os.path.join(root, "**", "*"), recursive=True)):
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                out[os.path.relpath(path, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)


# =====================================================================
# THE FIXTURE: her committed files, and her first pass recreated
# =====================================================================
def committed_files():
    battery = glob.glob(os.path.join(ROOT, "results", "live",
                                     "battery__%s__*__%s.json" % (MEMBER, RUN_ID)))
    copies = [p for p in glob.glob(os.path.join(ROOT, "results", "live", MEMBER, "*.json"))
              if not p.endswith("__judged.json") and load(p).get("run_id") == RUN_ID]
    return (battery[0] if len(battery) == 1 else None,
            copies[0] if len(copies) == 1 else None)


def make_tree(tmp, battery_src, copy_src):
    live = os.path.join(tmp, "live")
    os.makedirs(os.path.join(live, MEMBER))
    os.makedirs(os.path.join(tmp, "judge"))
    battery = os.path.join(live, os.path.basename(battery_src))
    copy_path = os.path.join(live, MEMBER, os.path.basename(copy_src))
    shutil.copyfile(battery_src, battery)
    shutil.copyfile(copy_src, copy_path)

    # Her first pass, as run_live_battery.py chained it: judge.main on the
    # member copy, whose queue is the 18 cases that ran after the resume.
    calls = {"n": 0}

    def fake(messages):
        calls["n"] += 1
        return fake_judge(messages, calls["n"])

    saved = judge.LIVE_CALL, judge.JUDGE_USAGE_DIR, sys.stdout, sys.excepthook
    judge.LIVE_CALL, judge.JUDGE_USAGE_DIR = fake, os.path.join(tmp, "judge")
    config.set_api_key(FAKE_KEY)
    sys.stdout = io.StringIO()
    try:
        judge.main([copy_path, "--by", "model", "--model", judge.DEFAULT_JUDGE_MODEL])
    finally:
        judge.LIVE_CALL, judge.JUDGE_USAGE_DIR, sys.stdout, sys.excepthook = saved
        config.set_api_key(None)
    return battery, copy_path, copy_path[:-len(".json")] + "__judged.json", calls["n"]


def run(tmp, argv, answer="judge", fake=fake_judge):
    """cj.main against the temporary tree. Returns (rc or SystemExit, calls, output)."""
    calls = {"live": 0, "key": 0, "input": 0, "cases": []}

    def live(messages):
        calls["live"] += 1
        return fake(messages, calls["live"])

    real_eval = judge.evaluate_outcome

    def recording(expected, actual, judge_model=None, doc=None):
        calls["cases"].append(actual["case_id"])
        return real_eval(expected, actual, judge_model, doc)

    def key(dry_run=False):
        calls["key"] += 1
        return FAKE_KEY

    def ask(prompt=""):
        calls["input"] += 1
        return answer

    saved = (cj.LIVE_DIR, judge.JUDGE_USAGE_DIR, judge.LIVE_CALL,
             judge.evaluate_outcome, rb.obtain_key, builtins.input,
             sys.stdout, sys.excepthook)
    cj.LIVE_DIR, judge.JUDGE_USAGE_DIR = os.path.join(tmp, "live"), os.path.join(tmp, "judge")
    judge.LIVE_CALL, judge.evaluate_outcome = live, recording
    rb.obtain_key, builtins.input = key, ask
    buf = io.StringIO()
    sys.stdout = buf
    try:
        rc = cj.main(argv)
    except SystemExit as exc:
        rc = exc
    finally:
        hook_restored = sys.excepthook is saved[7]
        (cj.LIVE_DIR, judge.JUDGE_USAGE_DIR, judge.LIVE_CALL,
         judge.evaluate_outcome, rb.obtain_key, builtins.input,
         sys.stdout, sys.excepthook) = saved
    calls["hook_restored"] = hook_restored
    return rc, calls, buf.getvalue()


def refused(rc):
    return isinstance(rc, SystemExit) and "REFUSING" in str(rc.code)


# =====================================================================
# 1 · THE DRY RUN
# =====================================================================
def test_dry_run(tmp, src):
    print("\n  1 · THE DRY RUN MAKES EVERY CHECK AND CHANGES NOTHING")
    battery, copy_path, judged, first_calls = make_tree(tmp, *src)
    first = load(judged)["judgement"]
    check("the recreated first pass judged 18 of 40 cases",
          first_calls == 18 and first["items_judged"] == 18, str(first))
    before = snapshot(tmp)
    rc, calls, out = run(tmp, ["--member", MEMBER, "--dry-run"])
    check("exits 0", rc == 0, str(rc))
    check("no call, no key prompt, no confirmation prompt",
          calls["live"] == calls["key"] == calls["input"] == 0, str(calls))
    check("no file written or changed", snapshot(tmp) == before)
    check("the banner counts 40 cases, 18 kept, 22 to judge",
          "40, one item each" in out and "already judged  18" in out
          and "to judge now    22" in out, out[-600:])
    check("the estimate comes from the first pass's measured cost",
          "US$%.4f" % (22 * COST_PER_CALL) in out, out[-600:])


# =====================================================================
# 2 · THE COMPLETION
# =====================================================================
def test_completion(tmp, src):
    print("\n  2 · THE COMPLETION JUDGES ONLY THE 22 PENDING CASES")
    battery, copy_path, judged, _ = make_tree(tmp, *src)
    first_doc = load(judged)
    kept = {q["case_id"]: q for q in first_doc["judgement_queue"]}
    pass1_usage = glob.glob(os.path.join(tmp, "judge", "*.json"))
    before = snapshot(tmp)

    rc, calls, out = run(tmp, ["--member", MEMBER])
    check("exits 0", rc == 0, "%s\n%s" % (rc, out[-800:]))
    check("22 judge calls, one per pending case", calls["live"] == 22, str(calls["live"]))
    check("none of the 18 already-judged cases was sent to the judge",
          not set(calls["cases"]) & set(kept), sorted(set(calls["cases"]) & set(kept)))
    check("the key was asked once, after the confirmation",
          calls["key"] == 1 and calls["input"] == 1, str(calls))
    check("the excepthook is restored", calls["hook_restored"])
    check("the key is cleared from config", config.api_key() != FAKE_KEY)

    after = snapshot(tmp)
    for label, path in (("battery file", battery), ("member copy", copy_path),
                        ("first pass's usage file", pass1_usage[0])):
        name = os.path.relpath(path, tmp)
        check("the %s is byte-identical" % label, before[name] == after[name])

    doc = load(judged)
    s = doc["judgement"]
    key_rows = harness.load_key(doc["problem"])
    rebuilt = rb.judgement_queue_for(load(battery)["results"], key_rows)
    check("40 judged, 0 pending",
          s["items_total"] == s["items_judged"] == 40 and s["items_pending"] == 0, str(s))
    check("passed + failed == judged", s["passed"] + s["failed"] == 40)
    check("the queue is the rebuilt queue, in run order",
          [q["case_id"] for q in doc["judgement_queue"]] == [q["case_id"] for q in rebuilt])
    check("the 18 earlier verdicts are kept exactly",
          all(q == kept[q["case_id"]] for q in doc["judgement_queue"]
              if q["case_id"] in kept))
    check("every new item names the judge model",
          all(q["graded_by"] == "model: %s" % judge.DEFAULT_JUDGE_MODEL
              for q in doc["judgement_queue"]))
    check("results are the battery's results", doc["results"] == load(battery)["results"])

    passes = s.get("passes") or []
    check("two passes recorded: 18 then 22",
          [p["items_judged"] for p in passes] == [18, 22], str(passes))
    check("pass 1 keeps its measured tokens",
          passes and passes[0]["judge_tokens_in"] == first_doc["judgement"]["judge_tokens_in"])
    check("the totals are the sum of both passes",
          s["judge_tokens_in"] == sum(p["judge_tokens_in"] for p in passes)
          and s["judge_tokens_out"] == sum(p["judge_tokens_out"] for p in passes))

    usage_files = sorted(glob.glob(os.path.join(tmp, "judge", "*.json")))
    new = [p for p in usage_files if p not in pass1_usage]
    check("one new usage file, named __<run id>__pass2 - a name judge.write_usage never writes",
          len(new) == 1 and new[0].endswith("__%s__pass2.json" % RUN_ID), str(usage_files))
    check("each pass records its measured cost",
          [p.get("cost_usd") for p in passes]
          == [round(18 * COST_PER_CALL, 6), round(22 * COST_PER_CALL, 6)], str(passes))
    if new:
        u = load(new[0])
        check("the usage file records 22 cases and their MEASURED cost",
              u["items_judged"] == 22 and abs(u["cost_usd"] - 22 * COST_PER_CALL) < 1e-9
              and u["cost_source"].startswith("measured"), str(u))
        check("it names the member, the judged file and the cases kept",
              u["graded_member"] == MEMBER and u["items_kept_from_earlier_passes"] == 18
              and u["judged_file"].endswith("__judged.json"))
        check("pass 2 in the judged file points at it",
              passes[-1]["usage_file"] == os.path.relpath(new[0], ROOT))
    written = "".join(json.dumps(load(p)) for p in [judged] + new)
    check("nothing key-shaped reaches the files", "sk-or-" not in written)

    first = {}
    for r in load(battery)["results"]:
        first.setdefault(r["case_id"], r["record"])
    unparseable_passes = [q["case_id"] for q in doc["judgement_queue"]
                          if q["verdict"] == "pass"
                          and "did not return parseable JSON" in str(first[q["case_id"]].get("reason"))]
    check("every pass on an unparseable record is listed for a person",
          s.get("needs_person_review") == unparseable_passes and unparseable_passes,
          "%s vs %s" % (s.get("needs_person_review"), unparseable_passes))
    check("listing a case for review leaves its verdict as the judge gave it",
          all(q["verdict"] == "pass" for q in doc["judgement_queue"]
              if q["case_id"] in (s.get("needs_person_review") or [])))
    check("the summary tells the person which cases to review",
          "PERSON REVIEW" in out and all(c in out for c in unparseable_passes), out[-500:])

    print("\n  3 · RUNNING IT AGAIN DOES NOTHING")
    before = snapshot(tmp)
    rc, calls, out = run(tmp, ["--member", MEMBER])
    check("exits 0 with nothing to judge",
          rc == 0 and "Nothing to do" in out, "%s %s" % (rc, out[-300:]))
    check("no call, no key prompt", calls["live"] == calls["key"] == 0)
    check("no file written or changed", snapshot(tmp) == before)


# =====================================================================
# 4 · STOPPED PART-WAY, THEN FINISHED
# =====================================================================
def test_partial(tmp, src):
    print("\n  4 · A PASS THAT STOPS PART-WAY KEEPS WHAT IT PAID FOR")
    battery, copy_path, judged, _ = make_tree(tmp, *src)
    rc, calls, out = run(tmp, ["--member", MEMBER], fake=failing_after(5))
    doc = load(judged)
    s = doc["judgement"]
    check("exits 1, because cases are still pending", rc == 1, "%s\n%s" % (rc, out[-500:]))
    check("the 5 verdicts it got are written: 23 judged, 17 pending",
          s["items_judged"] == 23 and s["items_pending"] == 17, str(s))
    usage = [p for p in glob.glob(os.path.join(tmp, "judge", "*.json"))
             if p.endswith("__pass2.json")]
    check("the spend before the failure is recorded",
          len(usage) == 1 and abs(load(usage[0])["cost_usd"] - 5 * COST_PER_CALL) < 1e-9
          and "402" in (load(usage[0])["stopped"] or ""), str(usage))

    kept = {q["case_id"]: q for q in doc["judgement_queue"] if q.get("verdict")}
    rc, calls, out = run(tmp, ["--member", MEMBER])
    doc = load(judged)
    s = doc["judgement"]
    check("the next run judges only the 17 left", calls["live"] == 17, str(calls["live"]))
    check("40 judged, 0 pending, three passes: 18, 5, 17",
          s["items_judged"] == 40 and s["items_pending"] == 0
          and [p["items_judged"] for p in s["passes"]] == [18, 5, 17], str(s))
    check("the 23 earlier verdicts are kept exactly",
          all(q == kept[q["case_id"]] for q in doc["judgement_queue"]
              if q["case_id"] in kept))
    check("pass 3 has its own usage file",
          len(glob.glob(os.path.join(tmp, "judge", "*__pass3.json"))) == 1)


# =====================================================================
# 5 · A RE-RUN OF THE SAME MEMBER, JUDGED THE SAME DAY
# =====================================================================
def other_run_usage(path, pass1):
    """The record a same-day re-run's judge writes under the same name."""
    other = dict(load(pass1), graded_file="results/live/li_yunke/other__6dfb98e18210.json",
                 items_judged=40, cost_usd=0.9)
    save(path, other)


def test_same_day_rerun(tmp_root, src):
    print("\n  5 · A SAME-DAY RE-RUN'S USAGE FILE IS NEVER MISTAKEN FOR PASS 1")
    tmp = tempfile.mkdtemp(dir=tmp_root)
    make_tree(tmp, *src)
    pass1 = glob.glob(os.path.join(tmp, "judge", "*.json"))[0]
    aside = pass1[:-len(".json")] + "__%s.json" % RUN_ID
    os.rename(pass1, aside)
    other_run_usage(pass1, aside)
    before = snapshot(tmp)
    rc, calls, out = run(tmp, ["--member", MEMBER, "--run-id", RUN_ID])
    doc = load(glob.glob(os.path.join(tmp, "live", MEMBER, "*__judged.json"))[0])
    passes = doc["judgement"]["passes"]
    after = snapshot(tmp)
    check("renamed aside, pass 1's record is still found by its contents",
          rc == 0 and (passes[0]["usage_file"] or "").endswith("__%s.json" % RUN_ID),
          "%s %s" % (rc, passes[0]))
    check("the estimate uses pass 1's cost, not the re-run's",
          "US$%.4f" % (22 * COST_PER_CALL) in out, out[-700:])
    check("the re-run's usage file and the renamed one are byte-identical",
          all(before[os.path.relpath(p, tmp)] == after[os.path.relpath(p, tmp)]
              for p in (pass1, aside)))
    check("this pass still writes __pass2",
          len(glob.glob(os.path.join(tmp, "judge", "*__pass2.json"))) == 1)

    tmp = tempfile.mkdtemp(dir=tmp_root)
    make_tree(tmp, *src)
    pass1 = glob.glob(os.path.join(tmp, "judge", "*.json"))[0]
    other_run_usage(pass1, pass1)                 # overwritten, not restored
    rc, calls, out = run(tmp, ["--member", MEMBER, "--run-id", RUN_ID])
    doc = load(glob.glob(os.path.join(tmp, "live", MEMBER, "*__judged.json"))[0])
    check("overwritten, pass 1 is recorded as NOT FOUND rather than the wrong file",
          rc == 0 and doc["judgement"]["passes"][0]["usage_file"] is None
          and "NOT FOUND" in out and "estimate" not in out, out[-700:])


# =====================================================================
# 6 · THE REFUSALS
# =====================================================================
def test_refusals(tmp_root, src):
    print("\n  6 · WHAT IT REFUSES TO MERGE OR JUDGE")

    def case(label, tamper, argv=("--member", MEMBER)):
        tmp = tempfile.mkdtemp(dir=tmp_root)
        paths = make_tree(tmp, *src)
        tamper(tmp, *paths[:3])
        before = snapshot(tmp)
        rc, calls, out = run(tmp, list(argv))
        check(label, refused(rc) and calls["live"] == calls["key"] == 0
              and snapshot(tmp) == before, "%s %s" % (rc, calls))

    def edit(path, change):
        doc = load(path)
        change(doc)
        save(path, doc)

    case("a changed judge prompt",
         lambda t, b, c, j: edit(j, lambda d: d["judgement"].update(
             judge_prompt_sha256="0" * 64)))
    case("earlier verdicts from another judge model",
         lambda t, b, c, j: edit(j, lambda d: d["judgement"].update(
             judged_by="model: other/judge")))
    case("an earlier verdict given on a different reason",
         lambda t, b, c, j: edit(j, lambda d: d["judgement_queue"][0].update(
             reason="edited")))
    case("a battery with a trial missing",
         lambda t, b, c, j: edit(b, lambda d: d["results"].pop()))
    case("a battery run on a different answer key",
         lambda t, b, c, j: edit(b, lambda d: d["fingerprint"].update(
             answer_key_sha256="0" * 64)))
    case("no member copy of the run", lambda t, b, c, j: os.remove(c))
    case("a judged file from another run",
         lambda t, b, c, j: edit(j, lambda d: d.update(run_id="000000000000")))

    def second_battery(t, b, c, j):
        edit_path = b.replace(RUN_ID, "111111111111")
        shutil.copyfile(b, edit_path)
        edit(edit_path, lambda d: d.update(run_id="111111111111"))
    case("two batteries and no --run-id", second_battery)

    tmp = tempfile.mkdtemp(dir=tmp_root)
    b, c, j, _ = make_tree(tmp, *src)
    second_battery(tmp, b, c, j)
    rc, calls, out = run(tmp, ["--member", MEMBER, "--run-id", RUN_ID, "--dry-run"])
    check("--run-id picks one of them", rc == 0, "%s %s" % (rc, out[-300:]))

    tmp = tempfile.mkdtemp(dir=tmp_root)
    make_tree(tmp, *src)
    before = snapshot(tmp)
    rc, calls, out = run(tmp, ["--member", MEMBER], answer="no")
    check("anything but 'judge' stops before the key, with nothing written",
          rc == 0 and calls["key"] == calls["live"] == 0 and snapshot(tmp) == before,
          "%s %s" % (rc, calls))


def main():
    print()
    print("=" * 70)
    print("  REHEARSING complete_judgement.py - free, offline, no key")
    print("=" * 70)
    src = committed_files()
    if None in src:
        check("li_yunke's committed battery %s and its member copy exist" % RUN_ID,
              False, "results/live/ does not hold them")
    else:
        root = tempfile.mkdtemp(prefix="complete_judgement_")
        try:
            for test in (test_dry_run, test_completion, test_partial):
                test(tempfile.mkdtemp(dir=root), src)
            test_same_day_rerun(root, src)
            test_refusals(root, src)
        finally:
            shutil.rmtree(root, ignore_errors=True)
    print()
    print("=" * 70)
    print("  %d passed, %d failed" % (len(PASSED), len(FAILED)))
    for f in FAILED:
        print("    FAILED: %s" % f)
    print("=" * 70)
    print()
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
