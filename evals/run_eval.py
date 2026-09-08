#!/usr/bin/env python3
"""
PE6201 · A2 scaffold — ENTRY POINT
====================================================================
    python3 run_eval.py              run every SCRIPTED case
    python3 run_eval.py REF-5602     run one case, showing every turn
    python3 run_eval.py --all        run every case in the work queue
    python3 run_eval.py --prompt     print what the model is told, and stop

THIS IS WHAT A MARKER RUNS. Clone, `python3 run_eval.py`, numbers come
back. No key, no network, no arguments. If that does not work on a
clean machine, D5(a) has failed and Technical Execution is capped.

Test it the way a marker will: clone your own repository into a fresh
folder and run it there. "Works on my laptop" has caught out every
cohort so far.
====================================================================
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config
from backends import SCRIPTS
from evals.harness import load_cases, load_key, report, run_set


def _flag_value(argv, name):
    """`--flag value` -> "value", or None. The file parses flags by hand
    already; this keeps that style rather than importing argparse for two
    options."""
    argv = list(argv or [])
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
            return argv[i + 1]
    return None


def main(argv):
    print()
    print(config.summary())
    print("data: %s" % config.data_root())

    # Flags that TAKE a value, so their value is not mistaken for a case
    # id. `--judge-model meta-llama/llama-3.1-8b-instruct` would otherwise
    # be read as "run the single case named meta-llama/...".
    _VALUED = ("--judge-model", "--judge-limit")
    rest, skip = [], False
    for a in argv[1:]:
        if skip:
            skip = False
            continue
        if a in _VALUED:
            skip = True
            continue
        rest.append(a)
    args = [a for a in rest if not a.startswith("-")]
    flags = {a for a in argv[1:] if a.startswith("-")}

    # ---- show exactly what the model is told, then stop ----------------
    if "--prompt" in flags:
        import prompt
        print()
        prompt.audit()
        return 0

    # ---- one named case, verbose --------------------------------------
    if args:
        case_id = args[0]
        print()
        print("-" * 68)
        print("  %s - every turn" % case_id)
        print("-" * 68)
        results, queue = run_set([case_id], verbose=True)
        if not results:
            return 1
        print()
        print("  DECISION RECORD")
        print(json.dumps(results[0]["record"], indent=2)[:2000])
        print()
        print("  CODE CHECK   %s" % ("PASS" if results[0]["passed"] else "FAIL"))
        for f in results[0]["fails"]:
            print("      %s" % f)
        print()
        print("  JUDGEMENT CHECK - not automated. Someone reads the reason")
        print("  and rules on each item:")
        for item in queue[0]["must_record"]:
            print("      [ ] %s" % item)
        print()
        return 0 if results[0]["passed"] else 1

    # ---- the set ------------------------------------------------------
    if "--all" in flags:
        cases = load_cases()
        print("\n  Running EVERY case in the work queue (%d)." % len(cases))
        print("  Cases with no script will stop the run - that is the")
        print("  scripted backend telling you to write one.")
    else:
        # Default: the whole labelled set. Every case is either hand
        # scripted or derived by the planner, so a clean clone runs all
        # of it with no key and no network - which is what D5(a) is.
        key = load_key()
        cases = [c for c in load_cases() if c in key]
        hand = sum(1 for c in cases if c in SCRIPTS)
        print("\n  Running all %d labelled case(s) - %d hand-scripted, "
              "%d planned." % (len(cases), hand, len(cases) - hand))
        print("  Grouping: %s (see src/backends/planner.py for the rule)."
              % config.GROUPING)

    if not cases:
        print("\n  Nothing to run for Problem %s." % config.PROBLEM)
        print("  config.PROBLEM is %r - is that the problem you chose?"
              % config.PROBLEM)
        return 1

    results, queue = run_set(cases)
    summary = report(results)

    # WHERE RESULTS GO. Anchored to the repository, never to the working
    # directory: a relative "results.json" lands wherever you happened to
    # launch python from, which is how six team members end up with six
    # partial result files and no way to tell which produced which number.
    # The name carries backend, prompt version and date, because
    # GUARDRAILS 7 requires a pass rate to be traceable to the run
    # that produced it.
    out_dir = os.path.join(ROOT, "results",
                           "scripted" if config.BACKEND == "scripted" else "live")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    slug = (config.MODEL.replace("/", "-") if config.BACKEND == "live"
            else "scripted")
    out_path = os.path.join(
        out_dir, "problem%s__%s__%s__%s.json"
                 % (config.PROBLEM, slug, config.PROMPT_VERSION, stamp))

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"config": config.summary(),
                   "backend": config.BACKEND,
                   "model": config.MODEL if config.BACKEND == "live" else None,
                   "prompt_version": config.PROMPT_VERSION,
                   "problem": config.PROBLEM,
                   "date": stamp,
                   "summary": summary,
                   "results": [{k: v for k, v in r.items()} for r in results],
                   "judgement_queue": queue}, fh, indent=2, default=str)
    print("  Wrote %s" % os.path.relpath(out_path, ROOT))
    print("  Commit it. Your result tables come from here, and a marker")
    print("  reads it alongside your report.")
    print()

    # ---- D4's SECOND CHECK -------------------------------------------
    # The judgement check runs as a PASS OVER THE RESULTS FILE, not inside
    # run_set. Three reasons, and each one is a bug avoided:
    #
    #   1. evals/harness.py is in battery_provenance.PINNED_SOURCES. A
    #      network call inside run_set changes the fingerprint every six
    #      members compare against.
    #   2. It would make the battery non-deterministic and non-resumable -
    #      a judge call inside a checkpointed loop cannot be replayed.
    #   3. It would spend live tokens DURING the battery, which is priced
    #      at 60 trials, not 60 trials plus 115 judge calls. The US$3
    #      ceiling is computed against the battery alone.
    #
    # Run as a pass, it is re-runnable, separately budgeted, and its spend
    # lands in results/judge/ where D6 can find it.
    if "--judge" in flags:
        judge_model = _flag_value(argv, "--judge-model")
        by = "model" if judge_model else "person"
        print("  Running D4's judgement check over that file...")
        print()
        from evals.graders import judge as judge_mod
        inner = [out_path, "--by", by]
        if judge_model:
            inner += ["--model", judge_model]
        limit = _flag_value(argv, "--judge-limit")
        if limit:
            inner += ["--limit", limit]
        return judge_mod.main(inner)

    print("  HALF THE CHECK IS DONE. D4 needs both kinds:")
    print("      python3 evals/graders/judge.py %s"
          % os.path.relpath(out_path, ROOT))
    print("  or re-run with --judge (add --judge-model <id> for a model).")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
