#!/usr/bin/env python3
"""
PE6201 · A2 — FINISH THE JUDGEMENT CHECK OF A RESUMED BATTERY  (D4)
====================================================================
    python3 experiments/complete_judgement.py --member li_yunke --dry-run
    python3 experiments/complete_judgement.py --member li_yunke

Before 57121af, a resumed battery's judgement_queue held only the cases
whose first trial ran after the resume. harness.run_set queues the trials
of its own process. li_yunke's battery (run e7dd3797c778) was interrupted
at trial 40 on 2026-09-14 and resumed, and the judge then graded 18 of her
40 cases. The runner fix protects future runs. This script finishes hers.

It rebuilds the queue with run_battery.judgement_queue_for, the function
the fixed runner uses, and judges only the cases that are still PENDING.

--------------------------------------------------------------------
WHAT IT NEVER TOUCHES

  * The battery file and the member copy. They stay exactly as the
    runner wrote them.
  * A verdict that was already given. It is kept as it is and never
    judged again. Re-judging a case and keeping whichever verdict reads
    better is editing numbers by another route. A kept verdict must come
    from the same judge model and judge prompt, on the same record, from
    the same answer key. Otherwise the script refuses to merge.
  * The first pass's usage record. judge.write_usage names its file by
    judge, member, model and date, so a second pass on the same day would
    overwrite a D6 input. This pass's record is named __<run id>__pass<N>.

WHAT IT WRITES

  * <member copy>__judged.json: every case, plus `judgement.passes`
    recording which pass judged how many cases, with its measured tokens.
  * results/judge/judge_usage__...json: this pass's MEASURED spend.

The key is asked at a hidden prompt, held in memory and never written.
--dry-run makes every check the real run makes, then stops before the
key: nothing is asked, nothing is spent, nothing is written.
====================================================================
"""
import argparse
import copy
import datetime
import glob
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config                                              # noqa: E402
from backends.backends import LiveFatalError               # noqa: E402
from evals import battery_provenance as prov               # noqa: E402
from evals import harness                                  # noqa: E402
from evals import run_battery as rb                        # noqa: E402
from evals.graders import judge                            # noqa: E402
from evals.metrics import UNPARSEABLE                      # noqa: E402

LIVE_DIR = os.path.join(ROOT, "results", "live")

# A kept verdict is the same measurement as a new one only if the judge saw
# the same item. These are the fields prepare_judgement_check writes.
SAME_ITEM_FIELDS = ("case_id", "decision", "reason", "must_record")


def rel(path):
    return os.path.relpath(path, ROOT)


def refuse(*lines):
    raise SystemExit("\n  REFUSING.\n" + "".join("  %s\n" % l for l in lines)
                     + "  Nothing was asked, spent or written.\n")


# =====================================================================
# FINDING THE RUN
# =====================================================================
def find_battery(member, run_id=None):
    """The member's live battery file: exactly one, or stop."""
    found = []
    for path in sorted(glob.glob(os.path.join(LIVE_DIR,
                                              "battery__%s__*.json" % member))):
        if path.endswith("__judged.json"):
            continue
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("dry_run") or doc.get("backend") != "live":
            continue
        if run_id and doc.get("run_id") != run_id:
            continue
        found.append((path, doc))
    if not found:
        refuse("No live battery for %r%s in %s."
               % (member, " with run id %s" % run_id if run_id else "",
                  rel(LIVE_DIR)))
    if len(found) > 1:
        refuse("%s has %d live batteries. Pass --run-id with one of:"
               % (member, len(found)),
               *["  %s  %s" % (d["run_id"], rel(p)) for p, d in found])
    return found[0]


def check_complete(doc, key):
    """Only a finished battery is judged. A halted one is resumed first."""
    fp = doc.get("fingerprint") or {}
    shape = fp.get("plan_shape") or {}
    results = doc.get("results") or []
    cases = {r["case_id"] for r in results}
    first_seen = {}
    for r in results:
        first_seen.setdefault(r["case_id"], r.get("trial"))

    problems = []
    if len(results) != shape.get("trials"):
        problems.append("%d results; the plan is %s trials"
                        % (len(results), shape.get("trials")))
    if len(cases) != shape.get("cases"):
        problems.append("%d cases; the plan is %s" % (len(cases), shape.get("cases")))
    if len({(r["case_id"], r.get("trial")) for r in results}) != len(results):
        problems.append("a (case, trial) pair appears twice")
    # judge.trajectory_of shows the judge each case's FIRST result in the
    # file, and the queue item is built from trial 1. They must be the same
    # record, or the judge reads one trial's trace beside another's reason.
    late = sorted(c for c, t in first_seen.items() if t != 1)
    if late:
        problems.append("the first result is not trial 1 for: %s" % ", ".join(late))
    unkeyed = sorted(cases - set(key))
    if unkeyed:
        problems.append("not in the answer key: %s" % ", ".join(unkeyed))
    key_path = os.path.join(config.data_root(),
                            "expected_outcomes_%s.json" % doc.get("problem"))
    if prov.sha256_file(key_path) != fp.get("answer_key_sha256"):
        problems.append("the answer key has changed since this battery ran, "
                        "so must_record would not be what the first pass judged")
    if problems:
        refuse("Run %s is not a complete battery on today's answer key:"
               % doc.get("run_id"), *["  - %s" % p for p in problems])


def find_member_copy(member, doc):
    """The copy run_live_battery.py made in results/live/<member>/, by run id."""
    found = []
    for path in sorted(glob.glob(os.path.join(LIVE_DIR, member, "*.json"))):
        if path.endswith("__judged.json"):
            continue
        with open(path, encoding="utf-8") as fh:
            copy_doc = json.load(fh)
        if copy_doc.get("run_id") == doc["run_id"]:
            found.append((path, copy_doc))
    if len(found) != 1:
        refuse("Expected one copy of run %s in %s, found %d."
               % (doc["run_id"], rel(os.path.join(LIVE_DIR, member)), len(found)),
               "The judged file is named after that copy.")
    path, copy_doc = found[0]
    if copy_doc.get("results") != doc.get("results"):
        refuse("%s carries run %s but its results differ from %s."
               % (rel(path), doc["run_id"], "the battery file"))
    return path, copy_doc


# =====================================================================
# THE EARLIER PASS
# =====================================================================
def earlier_verdicts(judged_path, doc, rebuilt, judge_model):
    """(earlier judged doc or None, {case_id: kept item}), checked item by item."""
    if not os.path.isfile(judged_path):
        return None, {}
    with open(judged_path, encoding="utf-8") as fh:
        judged = json.load(fh)
    if (judged.get("run_id") != doc["run_id"]
            or judged.get("results") != doc.get("results")):
        refuse("%s is not a judged copy of run %s." % (rel(judged_path), doc["run_id"]))

    given = {q["case_id"]: q for q in judged.get("judgement_queue") or []
             if q.get("verdict")}
    if not given:
        return judged, {}

    summary = judged.get("judgement") or {}
    want_by = "model: %s" % judge_model
    if summary.get("judged_by") != want_by:
        refuse("The earlier verdicts were %s, not %s."
               % (summary.get("judged_by"), want_by),
               "Verdicts from two instruments are not one judgement rate.")
    if summary.get("judge_prompt_sha256") != judge.prompt_sha256():
        refuse("The judge prompt has changed since the earlier pass "
               "(sha %s, now %s)." % (str(summary.get("judge_prompt_sha256"))[:12],
                                     judge.prompt_sha256()[:12]))
    rebuilt_by_case = {q["case_id"]: q for q in rebuilt}
    for cid, item in sorted(given.items()):
        want = rebuilt_by_case.get(cid)
        if item.get("graded_by") != want_by:
            refuse("%s was graded by %s, not %s." % (cid, item.get("graded_by"), want_by))
        if want is None or any(item.get(f) != want.get(f) for f in SAME_ITEM_FIELDS):
            refuse("%s's earlier verdict was given on a different item than the "
                   "rebuilt queue holds." % cid)
    return judged, given


def needs_person_review(queue, doc):
    """Cases the judge passed although the record it read is an unparseable reply.

    A record with no parseable reply cannot contain a must_record item, so
    that pass is the judge's error. On li_yunke's run 6dfb98e18210 the judge
    did exactly this for CLM-8941: both items "present", with "model did not
    return parseable JSON" as the evidence. They are listed for a person to
    rule on; no verdict is changed.
    """
    first = {}
    for r in doc.get("results") or []:
        first.setdefault(r["case_id"], r.get("record") or {})
    return [q["case_id"] for q in queue if q.get("verdict") == "pass"
            and UNPARSEABLE in str(first.get(q["case_id"], {}).get("reason") or "")]


def first_pass_usage(summary, judge_model, doc, copy_path):
    """The first pass's usage record, found by what it says, not by its name.

    judge.write_usage names the file judge + member + model + date, so a
    second battery by the same member, judged the same day, writes the same
    name. li_yunke's re-run on 2026-09-14 does exactly that. Any file with
    that stem counts, including one renamed aside, but only if it graded
    this copy, with this prompt, for this many cases.
    """
    stem = os.path.join(judge.JUDGE_USAGE_DIR, "judge_usage__%s__%s__%s__%s"
                        % (judge._slug(judge_model), judge._slug(doc.get("member")),
                           judge._slug(doc.get("model")), summary.get("date")))
    for path in sorted(glob.glob(stem + "*.json")):
        with open(path, encoding="utf-8") as fh:
            u = json.load(fh)
        if (u.get("graded_file") == rel(copy_path) and u.get("pass", 1) == 1
                and u.get("items_judged") == summary.get("items_judged")
                and u.get("judge_prompt_sha256") == summary.get("judge_prompt_sha256")):
            return path
    return None


def first_pass_entry(summary, judge_model, doc, copy_path):
    usage = first_pass_usage(summary, judge_model, doc, copy_path)
    cost = None
    if usage:
        with open(usage, encoding="utf-8") as fh:
            cost = json.load(fh).get("cost_usd")
    return {"pass": 1, "date": summary.get("date"),
            "items_judged": summary.get("items_judged"),
            "judge_tokens_in": summary.get("judge_tokens_in"),
            "judge_tokens_out": summary.get("judge_tokens_out"),
            "cost_usd": cost,
            "usage_file": rel(usage) if usage else None,
            "queue": "the judgement_queue the battery wrote"}


def estimate(passes, pending):
    """Cost for `pending` items at the rate earlier passes measured, or None."""
    usd = items = 0
    for p in passes:
        if not p.get("usage_file"):
            continue
        with open(os.path.join(ROOT, p["usage_file"]), encoding="utf-8") as fh:
            u = json.load(fh)
        usd += float(u.get("cost_usd") or 0)
        items += int(u.get("items_judged") or 0)
    return (usd / items * pending, usd, items) if items else None


# =====================================================================
# WRITING
# =====================================================================
def write_usage_record(judge_model, graded_file, doc, counts, pass_no, extra):
    """judge.write_usage's record, under a name no other judging pass writes.

    The run id and pass number are always in the name. judge.write_usage's
    own name has neither, so a same-day re-run of this member, judged by
    run_live_battery.py, cannot overwrite this record, and this record cannot
    overwrite that one.
    """
    final_dir = judge.JUDGE_USAGE_DIR
    tmp = tempfile.mkdtemp(prefix="judge_usage_")
    try:
        judge.JUDGE_USAGE_DIR = tmp
        made, _cost = judge.write_usage(judge_model, graded_file, counts["items"],
                                        counts["in"], counts["out"], counts["usd"],
                                        counts["measured"], doc.get("member"),
                                        doc.get("model"))
        with open(made, encoding="utf-8") as fh:
            record = json.load(fh)
    finally:
        judge.JUDGE_USAGE_DIR = final_dir
        shutil.rmtree(tmp, ignore_errors=True)

    stem = os.path.join(final_dir, "%s__%s" % (os.path.basename(made)[:-len(".json")],
                                              doc["run_id"]))
    dest, n = "%s__pass%d.json" % (stem, pass_no), pass_no
    while os.path.exists(dest):         # a pass whose judged file never got written
        n += 1
        dest = "%s__pass%d.json" % (stem, n)
    record.update(extra)
    write_checked(dest, record)
    return dest, record


def write_checked(path, payload):
    body = json.dumps(payload, indent=2, default=str)
    rb.assert_no_secret(body, config.api_key())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".partial"
    with open(part, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    os.replace(part, path)          # a crash never leaves half a judged file


# =====================================================================
# MAIN
# =====================================================================
def main(argv=None):
    ap = argparse.ArgumentParser(prog="complete_judgement.py")
    ap.add_argument("--member", required=True, help="roster key, e.g. li_yunke")
    ap.add_argument("--run-id", help="needed only if the member has several batteries")
    ap.add_argument("--dry-run", action="store_true",
                    help="check everything, then stop: no key, no spend, no writes")
    ap.add_argument("--spend-cap", type=float, default=judge.JUDGE_SPEND_CAP_USD)
    args = ap.parse_args(argv)
    judge_model = judge.DEFAULT_JUDGE_MODEL
    today = datetime.date.today().isoformat()

    battery_path, doc = find_battery(args.member, args.run_id)
    key_rows = harness.load_key(doc.get("problem"))
    check_complete(doc, key_rows)
    copy_path, copy_doc = find_member_copy(args.member, doc)
    judged_path = copy_path[:-len(".json")] + "__judged.json"

    rebuilt = rb.judgement_queue_for(doc["results"], key_rows)
    earlier, given = earlier_verdicts(judged_path, doc, rebuilt, judge_model)
    queue = [given.get(item["case_id"], item) for item in rebuilt]
    pending = [q for q in queue if not q.get("verdict")]

    judge.refuse_self_grading(doc, judge_model)
    roster_models = {m.get("model") for m in prov.load_roster().get("members", [])}
    if judge_model in roster_models:
        refuse("The judge %s is on the battery roster." % judge_model)

    prev = (earlier or {}).get("judgement") or {}
    passes = copy.deepcopy(prev.get("passes") or
                           ([first_pass_entry(prev, judge_model, doc, copy_path)]
                            if given else []))
    guess = estimate(passes, len(pending))

    print()
    print("=" * 68)
    print("  D4 · FINISH THE JUDGEMENT CHECK OF A RESUMED BATTERY")
    print("=" * 68)
    print("  member          %s (%s)" % (doc["member"], doc.get("full_name")))
    print("  graded model    %s · prompt %s · run %s"
          % (doc["model"], doc.get("prompt_version"), doc["run_id"]))
    print("  battery file    %s   (read only)" % rel(battery_path))
    print("  judged file     %s" % rel(judged_path))
    print("  cases           %d, one item each from trial 1" % len(queue))
    print("  already judged  %d - kept as they are, not judged again" % len(given))
    print("  to judge now    %d" % len(pending))
    print("  judge           %s · prompt sha %s"
          % (judge_model, judge.prompt_sha256()[:12]))
    for p in passes:
        print("  pass %d usage    %s" % (p["pass"], p.get("usage_file") or
                                        "NOT FOUND - no usage record graded this copy"))
    if guess:
        print("  estimate        about US$%.4f  (measured US$%.5f for %d case(s) so far)"
              % guess)
    print("  spend cap       US$%.2f" % args.spend_cap)
    print("=" * 68)

    if not pending:
        print("\n  Every case already has a verdict. Nothing to do.\n")
        return 0
    print("  pending: %s" % ", ".join(q["case_id"] for q in pending))
    if args.dry_run:
        print("\n  DRY RUN - every check passed. No key asked, nothing spent, "
              "nothing written.\n")
        return 0

    print()
    if input("  Type 'judge' to proceed, anything else stops: ").strip() != "judge":
        print("\n  Stopped. Nothing was spent and nothing was written.\n")
        return 0

    key = rb.obtain_key(False)
    config.set_api_key(key)
    restore_hook = judge.install_scrubbing_excepthook(key)

    # judge_by_model returns its totals only when it finishes. A fatal HTTP
    # error or Ctrl-C mid-pass loses them, although every call before it was
    # billed. So count at the call, and keep what was judged either way.
    tally = {"calls": 0, "in": 0, "out": 0, "usd": 0.0, "measured": True}
    real_call = judge.LIVE_CALL

    def counted(messages):
        content, usage, meta = real_call(messages)
        u = usage or {}
        tally["calls"] += 1
        tally["in"] += int(u.get("prompt_tokens") or 0)
        tally["out"] += int(u.get("completion_tokens") or 0)
        if u.get("cost") is not None:
            tally["usd"] += float(u["cost"])
        else:
            tally["measured"] = False
        return content, usage, meta

    stopped = None
    judge.LIVE_CALL = counted
    try:
        print()
        try:
            t_in, t_out, usd, measured = judge.judge_by_model(
                pending, doc, judge_model, key_rows, args.spend_cap)
        except LiveFatalError as err:
            stopped = "the judge could not continue: %s" % err
        except KeyboardInterrupt:
            stopped = "interrupted"
        finally:
            judge.LIVE_CALL = real_call
        if stopped:
            t_in, t_out, usd, measured = (tally["in"], tally["out"],
                                          tally["usd"], tally["measured"])
            print("\n  STOPPED - %s" % stopped)

        newly = [q for q in pending if q.get("verdict")]
        if not newly and not tally["calls"]:
            print("  Nothing was judged and nothing was spent.\n")
            return 2

        pass_no = len(passes) + 1
        counts = {"items": len(newly), "in": t_in, "out": t_out,
                  "usd": usd, "measured": measured}
        usage_path, usage = write_usage_record(
            judge_model, copy_path, doc, counts, pass_no,
            {"pass": pass_no, "judged_file": rel(judged_path),
             "items_kept_from_earlier_passes": len(given),
             "stopped": stopped})

        passes.append({"pass": pass_no, "date": today,
                       "items_judged": len(newly),
                       "judge_tokens_in": t_in, "judge_tokens_out": t_out,
                       "cost_usd": usage["cost_usd"],
                       "usage_file": rel(usage_path),
                       "queue": ("rebuilt from every case's first trial by "
                                 "evals/run_battery.judgement_queue_for; cases "
                                 "already judged were kept, not judged again"),
                       "stopped": stopped})
        out = copy.deepcopy(earlier if earlier is not None else copy_doc)
        out["judgement_queue"] = queue
        judged = [q for q in queue if q.get("verdict")]
        out["judgement"] = {
            "judged_by": "model: %s" % judge_model,
            "judge_prompt_sha256": judge.prompt_sha256(),
            "items_total": len(queue),
            "items_judged": len(judged),
            "items_pending": len(queue) - len(judged),
            "passed": sum(1 for q in judged if q["verdict"] == "pass"),
            "failed": sum(1 for q in judged if q["verdict"] == "fail"),
            "judge_tokens_in": sum(int(p.get("judge_tokens_in") or 0) for p in passes),
            "judge_tokens_out": sum(int(p.get("judge_tokens_out") or 0) for p in passes),
            "date": today,
            "passes": passes,
            "needs_person_review": needs_person_review(queue, doc),
        }
        write_checked(judged_path, out)
    finally:
        sys.excepthook = restore_hook
        config.set_api_key(None)

    s = out["judgement"]
    print()
    print("=" * 68)
    print("  %d of %d judged · %d pass · %d fail · %d PENDING"
          % (s["items_judged"], s["items_total"], s["passed"], s["failed"],
             s["items_pending"]))
    if s["items_pending"]:
        print("  Run this again to judge the rest; judged cases are kept.")
    if s["needs_person_review"]:
        print("  PERSON REVIEW: the judge passed %s, but each of those records"
              % ", ".join(s["needs_person_review"]))
        print("  is an unparseable reply. Not a pass until a person rules on it.")
    print("=" * 68)
    print("  Wrote %s" % rel(judged_path))
    print("  Judge spend  %d in / %d out tokens · US$%.5f%s"
          % (t_in, t_out, usage["cost_usd"],
             "" if measured else "  (PARTIAL - not a D6 figure)"))
    print("  Wrote %s" % rel(usage_path))
    print("  ^ a D6 input, alongside every earlier pass's usage file.")
    print()
    return 0 if not s["items_pending"] else 1


if __name__ == "__main__":
    sys.exit(main())
