#!/usr/bin/env python3
"""
PE6201 · A2 — REHEARSE provider_audit.py  (free, offline)
====================================================================
    python3 experiments/test_provider_audit.py

Checks the audit against li_yunke's two archived qwen3-235b batteries,
whose provider counts were measured by hand on 2026-09-14, and against
small synthetic checkpoints for the verdicts a teammate will see.
====================================================================
"""
import contextlib
import glob
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "experiments"))

import provider_audit as pa                                # noqa: E402

PASSED, FAILED = [], []

# Measured by hand on 2026-09-14: (DeepInfra calls, unparseable replies,
# [passed, trials] that reached DeepInfra, [passed, trials] that never did).
MEASURED = {"e7dd3797c778": (19, 12, [2, 18], [39, 42]),
            "6dfb98e18210": (23, 16, [3, 21], [34, 39])}


def check(label, condition, detail=""):
    (PASSED if condition else FAILED).append(label)
    print("  %s  %s%s" % ("PASS" if condition else "FAIL", label,
                          "" if condition else "   <- %s" % detail))


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        out = fn(*args)
    return out, buf.getvalue()


def trial(case, passed, providers, reason="done"):
    return {"kind": "trial", "case_id": case, "trial": 1, "passed": passed,
            "record": {"reason": reason,
                       "turn_usage": [{"usage": {}, "meta": {"provider": p}}
                                      for p in providers]}}


def write_checkpoint(tmp, name, trials, dry_run=False):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "header", "member": "someone", "model": "a/model",
                             "prompt_version": "v2", "run_id": "run", "dry_run": dry_run}) + "\n")
        for t in trials:
            fh.write(json.dumps(t) + "\n")
    return path


def test_archived_runs():
    print("\n  1 · LI YUNKE'S TWO RUNS, AGAINST THE HAND COUNT")
    for run_id, (calls, unparse, reached, never) in MEASURED.items():
        found = glob.glob(os.path.join(ROOT, "results", "*", "battery__li_yunke__*__%s.json" % run_id)) \
            + glob.glob(os.path.join(ROOT, "results", "archive", "live",
                                     "battery__li_yunke__*__%s.json" % run_id))
        if len(found) != 1:
            check("run %s is on disk once" % run_id, False, str(found))
            continue
        header, trials = pa.load(found[0])
        c, u, r = pa.audit(trials)
        check("%s: %d DeepInfra calls" % (run_id, calls), c["DeepInfra"] == calls, str(c))
        check("%s: %d unparseable replies, every one DeepInfra's" % (run_id, unparse),
              u["DeepInfra"] == unparse and sum(u.values()) == unparse, str(u))
        check("%s: reached DeepInfra %d/%d, never %d/%d" % (run_id, reached[0], reached[1],
                                                           never[0], never[1]),
              r[True] == reached and r[False] == never, str(r))
        rc, out = quiet(pa.report, found[0], header, trials)
        check("%s: the verdict is FAIL, exit 1" % run_id, rc == 1 and "FAIL:" in out, out[-300:])
        rc, out = quiet(pa.main, ["--ignored", "NoSuchProvider", found[0]])
        check("%s: with another ignored list it is OK" % run_id, rc == 0 and "OK:" in out)


def test_synthetic(tmp):
    print("\n  2 · WHAT A TEAMMATE SEES")
    clean = write_checkpoint(tmp, "clean.jsonl", [trial("A", True, ["GMICloud", "Novita"]),
                                                  trial("B", False, ["Parasail"])])
    rc, out = quiet(pa.main, [clean])
    check("a checkpoint with no DeepInfra call is OK, exit 0",
          rc == 0 and "OK: no call reached DeepInfra  (3 calls, 3 providers)" in out, out)

    dirty = write_checkpoint(tmp, "dirty.jsonl",
                             [trial("A", True, ["GMICloud"]),
                              trial("B", False, ["GMICloud", "DeepInfra"],
                                    "model did not return parseable JSON")])
    rc, out = quiet(pa.main, [clean, dirty])
    check("one DeepInfra call anywhere makes the exit 1", rc == 1 and "FAIL: 1 call" in out, out)
    _h, trials = pa.load(dirty)
    _c, u, _r = pa.audit(trials)
    check("an unparseable reply is charged to the LAST call's provider",
          u == {"DeepInfra": 1}, str(u))

    old = {"case_id": "C", "passed": True, "record": {"provider": "Novita", "reason": "x"}}
    check("a record without turn_usage falls back to record.provider",
          pa.audit([old])[0] == {"Novita": 1})

    dry = write_checkpoint(tmp, "dry.jsonl", [trial("A", True, [])], dry_run=True)
    rc, out = quiet(pa.main, [dry])
    check("a dry run is reported as such, exit 0", rc == 0 and "dry run" in out, out)


def main():
    print()
    print("=" * 70)
    print("  REHEARSING provider_audit.py - free, offline")
    print("=" * 70)
    test_archived_runs()
    with tempfile.TemporaryDirectory() as tmp:
        test_synthetic(tmp)
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
