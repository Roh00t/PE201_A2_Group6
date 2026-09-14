#!/usr/bin/env python3
"""
PE6201 · A2 — WHICH PROVIDER SERVED EACH CALL  (D5b)
====================================================================
    python3 experiments/provider_audit.py                      # every live and archived battery
    python3 experiments/provider_audit.py results/live/battery__shen_bowen__*.json
    python3 experiments/provider_audit.py results/live/checkpoints/battery__<you>__<run>.jsonl

OpenRouter sends each call on a model id to one of several providers, and
the backend records which one answered (turn_usage[].meta.provider).
li_yunke's two qwen3-235b batteries on 2026-09-14 show why that matters.
DeepInfra answered 28 of its 42 calls with a blank line after every word
("an\\n\\nerror"), which is not an action. The other nine providers
answered 412 calls without one. The same model and prompt scored 41/60
and 37/60, depending on how many trials reached DeepInfra.

From that day, every battery still to run uses an OpenRouter account with
DeepInfra in Ignored Providers (openrouter.ai/settings/privacy). This
script checks that from the records instead of trusting the setting. It
exits 1 if any audited file has a call answered by an ignored provider.

Free. It reads files already on disk, so it also works on a checkpoint
while a battery is still running.
====================================================================
"""
import argparse
import collections
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals.metrics import UNPARSEABLE                      # noqa: E402

IGNORED = ("DeepInfra",)


def load(path):
    """(header, trials) from a battery results file or a checkpoint."""
    with open(path, encoding="utf-8") as fh:
        if path.endswith(".jsonl"):
            rows = [json.loads(line) for line in fh if line.strip()]
            header = next((r for r in rows if r.get("kind") in (None, "header")), {})
            return header, [r for r in rows if r.get("kind") == "trial"]
        doc = json.load(fh)
    return doc, doc.get("results") or []


def providers_of(record):
    """The provider of every call in one trial, in order."""
    turns = record.get("turn_usage") or []
    if turns:
        return [(t.get("meta") or {}).get("provider") or "unknown" for t in turns]
    return [record["provider"]] if record.get("provider") else []


def audit(trials, ignored=IGNORED):
    """Calls and unparseable replies per provider, and pass counts split by
    whether a trial reached an ignored provider. An unparseable reply is
    charged to the provider of the trial's LAST call, the one whose reply
    could not be read."""
    calls, unparseable = collections.Counter(), collections.Counter()
    reached = {True: [0, 0], False: [0, 0]}          # [passed, trials]
    for r in trials:
        rec = r.get("record") or {}
        provs = providers_of(rec)
        calls.update(provs)
        if provs and UNPARSEABLE in str(rec.get("reason") or ""):
            unparseable[provs[-1]] += 1
        side = reached[any(p in ignored for p in provs)]
        side[0] += bool(r.get("passed"))
        side[1] += 1
    return calls, unparseable, reached


def report(path, header, trials, ignored=IGNORED):
    """Print one file's audit. Returns 1 if an ignored provider answered."""
    print()
    print("  %s · %s · %s · run %s · %d trials, %d passed"
          % (header.get("member"), header.get("model"), header.get("prompt_version"),
             header.get("run_id"), len(trials), sum(1 for r in trials if r.get("passed"))))
    print("  %s" % os.path.relpath(path, ROOT))
    if header.get("dry_run"):
        print("    dry run - scripted, no provider answered anything")
        return 0
    calls, unparseable, reached = audit(trials, ignored)
    if not calls:
        print("    no provider recorded")
        return 0
    print("    %-14s %6s   %s" % ("provider", "calls", "unparseable replies"))
    for name, n in calls.most_common():
        u = unparseable[name]
        print("    %-14s %6d   %-12s%s" % (name, n, "%d (%.1f%%)" % (u, 100.0 * u / n) if u else "0",
                                         "<- IGNORED" if name in ignored else ""))
    bad = sum(calls[p] for p in ignored)
    names = "/".join(ignored)
    if not bad:
        print("    OK: no call reached %s  (%d calls, %d providers)"
              % (names, sum(calls.values()), len(calls)))
        return 0
    print("    trials that reached %s   %d/%d passed" % (names, reached[True][0], reached[True][1]))
    print("    trials that never did    %d/%d passed" % (reached[False][0], reached[False][1]))
    print("    FAIL: %d call(s) answered by %s." % (bad, names))
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="provider_audit.py")
    ap.add_argument("paths", nargs="*",
                    help="battery .json or checkpoint .jsonl files; "
                         "default: every live and archived battery")
    ap.add_argument("--ignored", action="append",
                    help="a provider that must not appear (default DeepInfra); repeatable")
    args = ap.parse_args(argv)
    ignored = tuple(args.ignored or IGNORED)
    paths = args.paths or sorted(
        glob.glob(os.path.join(ROOT, "results", "live", "battery__*.json"))
        + glob.glob(os.path.join(ROOT, "results", "archive", "live", "battery__*.json")))
    worst = 0
    for path in paths:
        header, trials = load(path)
        worst = max(worst, report(path, header, trials, ignored))
    print()
    return worst


if __name__ == "__main__":
    sys.exit(main())
