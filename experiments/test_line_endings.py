#!/usr/bin/env python3
"""
PE6201 · A2 — REHEARSE evals/line_endings.py  (free, offline)
====================================================================
    python3 experiments/test_line_endings.py

A Windows checkout of the same commit records different hashes for the
answer key, the fixtures and the pinned sources. These checks show the
equivalence is exact:
  - a CRLF copy of today's tree matches;
  - a one-byte change does not;
  - the batteries committed from Windows checkouts pass stage.py --status
    and aggregate_battery.py, and a real difference is still reported.
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
for p in (os.path.join(ROOT, "src"), ROOT, os.path.join(ROOT, "experiments", "post_freeze")):
    if p not in sys.path:
        sys.path.insert(0, p)

import config                                              # noqa: E402
import stage                                               # noqa: E402
from evals import aggregate_battery as ab                  # noqa: E402
from evals import battery_provenance as prov               # noqa: E402
from evals import line_endings as le                       # noqa: E402

PASSED, FAILED = [], []
WINDOWS_RUNS = ("shen_bowen", "xia_yanran")      # committed 2026-09-14 from CRLF checkouts


def check(label, condition, detail=""):
    (PASSED if condition else FAILED).append(label)
    print("  %s  %s%s" % ("PASS" if condition else "FAIL", label,
                          "" if condition else "   <- %s" % detail))


def windows_fingerprint(tmp, edit=None):
    """What a Windows checkout of today's tree records: every file written
    with CRLF endings, then hashed with battery_provenance's own functions.
    `edit` is (relative path, bytes to append) for a one-byte change."""
    def crlf(path):
        rel = os.path.relpath(path, ROOT)
        with open(path, "rb") as fh:
            data = fh.read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        if edit and edit[0] == rel:
            data += edit[1]
        dest = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
        return prov.sha256_file(dest)

    data = config.data_root()
    fixtures = os.path.join(data, "data_A")
    return {
        "answer_key_sha256": crlf(os.path.join(data, "expected_outcomes_A.json")),
        "fixtures_sha256": prov.sha256_json({f: crlf(os.path.join(fixtures, f))
                                             for f in sorted(os.listdir(fixtures))
                                             if f.endswith(".json")}),
        "sources_sha256": {p: crlf(os.path.join(ROOT, p)) for p in prov.PINNED_SOURCES},
    }


def committed(member):
    paths = glob.glob(os.path.join(ROOT, "results", "live", "battery__%s__*.json" % member))
    if len(paths) != 1:
        return None
    with open(paths[0], encoding="utf-8") as fh:
        return json.load(fh)


def test_equivalence(tmp):
    print("\n  1 · THE EQUIVALENCE IS EXACT")
    forms = le.variants("A")
    ok, eols = le.same_content(prov.fingerprint("A"), forms)
    check("today's own fingerprint matches today's content", ok, str(eols))

    ok, eols = le.same_content(windows_fingerprint(os.path.join(tmp, "win")), forms)
    check("a CRLF copy of today's tree matches, as a Windows checkout", ok and "crlf" in eols,
          "%s %s" % (ok, eols))

    source = prov.PINNED_SOURCES[0]
    ok, _ = le.same_content(windows_fingerprint(os.path.join(tmp, "src"), (source, b"#")), forms)
    check("one byte added to %s does not match" % source, not ok)

    key = os.path.relpath(os.path.join(config.data_root(), "expected_outcomes_A.json"), ROOT)
    ok, _ = le.same_content(windows_fingerprint(os.path.join(tmp, "key"), (key, b" ")), forms)
    check("one byte added to the answer key does not match", not ok)

    fp = windows_fingerprint(os.path.join(tmp, "missing"))
    fp["sources_sha256"].pop(source)
    check("a fingerprint missing a pinned source does not match",
          not le.same_content(fp, forms)[0])


def test_committed_batteries():
    print("\n  2 · THE BATTERIES COMMITTED FROM WINDOWS CHECKOUTS")
    forms = le.variants("A")
    frozen_tree = not os.path.exists(os.path.join(ROOT, "src", "final_check.py"))
    for member in WINDOWS_RUNS:
        doc = committed(member)
        if doc is None:
            check("%s has one committed battery" % member, False)
            continue
        fp = doc["fingerprint"]
        check("%s: answer key and fixtures are today's data with CRLF endings" % member,
              all(le.form_of(k, fp[k], forms) == "crlf"
                  for k in ("answer_key_sha256", "fixtures_sha256")))
        if frozen_tree:
            ok, eols = le.same_content(fp, forms)
            check("%s: every pinned source is today's content with CRLF endings" % member,
                  ok and eols == {"crlf"}, str(eols))
    rohit = committed("rohit_panda")
    if rohit and frozen_tree:
        ok, eols = le.same_content(rohit["fingerprint"], forms)
        check("rohit_panda's LF battery still matches as LF", ok and eols == {"lf"}, str(eols))

    runs = ab.load()
    problems = ab.check_comparable(runs)
    check("aggregate_battery reports no drift for the Windows checkouts",
          not any("answer_key" in p or "fixtures" in p for p in problems), str(problems))
    found = ab.windows_checkouts(runs)
    check("aggregate_battery names them in a note, and no LF run",
          set(WINDOWS_RUNS) <= set(found) and "rohit_panda" not in found, str(found))

    fake = dict(runs[0][1], member="someone_else",
                fingerprint=dict(runs[0][1]["fingerprint"], answer_key_sha256="0" * 64))
    problems = ab.check_comparable(runs + [("fake.json", fake)])
    check("aggregate_battery still reports a genuinely different answer key",
          any("answer_key_sha256 DIFFERS" in p for p in problems), str(problems))

    if frozen_tree:
        with contextlib.redirect_stdout(io.StringIO()):
            rows = stage.member_status()
        by = {r[0]: r for r in rows}
        check("stage.py --status matches every roster member",
              all(r[3] for r in rows), str([r[0] for r in rows if not r[3]]))
        check("stage.py labels the Windows checkouts, and only them",
              all((by[m][4] or "").startswith("Windows line endings") for m in WINDOWS_RUNS)
              and not by["rohit_panda"][4], str([(r[0], r[4]) for r in rows]))


def main():
    print()
    print("=" * 70)
    print("  REHEARSING evals/line_endings.py - free, offline")
    print("=" * 70)
    with tempfile.TemporaryDirectory() as tmp:
        test_equivalence(tmp)
    test_committed_batteries()
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
