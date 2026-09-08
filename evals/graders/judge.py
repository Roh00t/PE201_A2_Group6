#!/usr/bin/env python3
"""
PE6201 · A2 — THE JUDGEMENT CHECK  (D4, the half that was never run)
====================================================================
    python3 evals/graders/judge.py <results.json>                  # a person
    python3 evals/graders/judge.py <results.json> --by model       # a model
    python3 evals/graders/judge.py <results.json> --by model --limit 3

D4 requires TWO kinds of check and the repository shipped one. Every
results file already carries a `judgement_queue` whose items look like

    {"case_id", "decision", "reason", "must_record",
     "verdict": null, "graded_by": null}

Nothing filled `verdict`. This file does - by a person for free, or by a
second model for a few cents.

--------------------------------------------------------------------
FOUR THINGS THIS REFUSES TO DO, AND WHY

1 · IT WILL NOT LET A MODEL GRADE ITSELF. The brief: "use a different
    model from the one being graded." If --model equals the model that
    produced the results file, this aborts. A model marking its own
    homework is not a measurement, and the failure is silent otherwise.

2 · IT WILL NOT WRITE AN HTTP CLIENT. backends.LIVE_CALL already has
    retry with backoff on 429/5xx honouring Retry-After, immediate abort
    on a typo'd model id, an output token cap, reasoning disabled, and
    measured usage returned. A second client would have none of that,
    and one 429 mid-judging would kill the run.

3 · IT WILL NOT OVERWRITE THE INPUT. Output goes to <input>__judged.json.
    The ungraded file stays exactly as the harness wrote it, so judging
    can be re-run, compared, or thrown away.

4 · IT WILL NOT PUT THE KEY ANYWHERE PERSISTENT. Read at call time via
    config.api_key(), never written to a file, never echoed, never in a
    results file. See GUARDRAILS.md section 4.4.

--------------------------------------------------------------------
THIS IS LIVE SPEND OUTSIDE THE D5(b) BATTERY.

It does not pass through run_battery, so it never reaches
logs/battery/decisions__*.jsonl and D6 would under-report the real
OpenRouter bill. Every model run therefore writes

    results/judge/judge_usage__<model>__<date>.json

with MEASURED tokens, so Bowen can add it as a D6 input instead of
someone transcribing a printed number by hand. That is how a wrong
number reaches a report.
====================================================================
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config                                                    # noqa: E402
from backends.backends import (LIVE_CALL, LiveFatalError,        # noqa: E402
                               LiveTransportError)

PROMPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "judge_prompt.md")
JUDGE_USAGE_DIR = os.path.join(ROOT, "results", "judge")

# ---------------------------------------------------------------------
# THE JUDGE MODEL. Cheap tier, deliberately.
#
# The judge is a measuring instrument, not the thing being measured, and
# it is live spend on top of a US$3-per-member ceiling that the battery
# has already been sized against. 115 must_record items across 40 cases
# is roughly 115 calls; at frontier prices that is a second battery
# nobody budgeted for.
#
# It must ALSO not be a model any battery member is running - see
# refuse_self_grading(). Check evals/battery_roster.json before changing
# this string.
# ---------------------------------------------------------------------
DEFAULT_JUDGE_MODEL = "meta-llama/llama-3.1-8b-instruct"

# Judging is a short, bounded task: read a record, emit a small JSON
# object. It does not need the 1024-token completion budget an agent turn
# gets, and a smaller cap is a smaller bill.
JUDGE_MAX_TOKENS = 700

# A ceiling on the judging pass itself, in US dollars. Judging is not the
# experiment; if it costs more than this, something is wrong with the
# model id or the item count, and stopping is cheaper than finding out
# from a billing page.
JUDGE_SPEND_CAP_USD = 0.50


# =====================================================================
# THE KEY  (non-interactive by design)
# =====================================================================
def install_scrubbing_excepthook(key):
    """Never let the key reach a terminal via a traceback.

    Same guard run_battery.py installs. Judging is the other place in
    this repository that holds a live key, and a stack trace pasted into
    a group chat is the most likely way one escapes.
    """
    original = sys.excepthook

    def scrub(exc_type, exc, tb):
        import traceback
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        sys.stderr.write(text.replace(key, "sk-or-***REDACTED***") if key
                         else text)

    sys.excepthook = scrub
    return original


def resolve_key(allow_dotenv=False):
    """The key, without ever blocking on a prompt.

    config.api_key() reads a runtime override first and OPENROUTER_API_KEY
    second, so

        OPENROUTER_API_KEY=sk-or-... python3 evals/graders/judge.py ...

    runs unattended - which is what an automated verification needs.

    ON .env, AND WHY IT IS NOT THE DEFAULT. Reading the key from a file
    on disk contradicts GUARDRAILS.md 4.4, and python-dotenv would be the
    first dependency in a repository whose README promises "standard
    library only - nothing to install". So: no dependency, and the file
    path is opt-in behind --allow-dotenv. The parser below is nine lines
    of stdlib, and it still never writes the key anywhere.
    """
    key = config.api_key()
    if key:
        return key
    if allow_dotenv:
        path = os.path.join(ROOT, ".env")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("OPENROUTER_API_KEY"):
                        _, _, value = line.partition("=")
                        value = value.strip().strip('"').strip("'")
                        if value:
                            config.set_api_key(value)   # memory only
                            return value
    return ""


# =====================================================================
# LOADING, AND THE SELF-GRADING REFUSAL
# =====================================================================
def load_results(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def refuse_self_grading(doc, judge_model):
    """MANDATORY. The brief requires a different model from the graded one."""
    graded = doc.get("model")
    if graded and judge_model and graded.strip() == judge_model.strip():
        raise SystemExit(
            "\n  REFUSING TO JUDGE.\n"
            "  The results file was produced by %r and you asked %r to\n"
            "  grade it. A model marking its own homework is not a\n"
            "  measurement - the brief requires a different model.\n"
            "  Pass --model with something else.\n" % (graded, judge_model))


def prompt_sha256():
    with open(PROMPT_PATH, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# =====================================================================
# RENDERING ONE ITEM FOR THE JUDGE
# =====================================================================
def trajectory_of(doc, case_id):
    """The agent's tool calls in order, plus its decision.

    Taken from the run record's `evidence` list, which loop_agent
    appends to on every call INCLUDING failed ones - a trace that hides
    the bad call cannot be used to diagnose it.
    """
    for r in doc.get("results", []):
        if r.get("case_id") == case_id:
            rec = r.get("record") or {}
            calls = rec.get("evidence") or []
            return ("tool calls: %s\ndecision: %s\nturns: %s"
                    % (" -> ".join(calls) if calls else "(none recorded)",
                       rec.get("decision"), rec.get("turns")))
    return "(no run record found for this case)"


def render_prompt(template, item, doc, expected_decision):
    # A JSON ARRAY, not a numbered list. The prompt also carries numbered
    # rules about the output format, and a numbered list of items sitting
    # next to a numbered list of rules is an invitation for the judge to
    # rule on the rules - which is exactly what the first fake-model test
    # of this file did, returning 15 verdicts for 5 items.
    must = json.dumps(item.get("must_record") or [], indent=2)
    return (template
            .replace("{expected_outcome}", str(expected_decision or "unknown"))
            .replace("{actual_trajectory}", trajectory_of(doc, item["case_id"]))
            .replace("{reason}", item.get("reason") or "(no reason recorded)")
            .replace("{must_record}", must or "(no required items)"))


# =====================================================================
# PARSING — MALFORMED JSON IS A FAIL, NEVER A CRASH
# =====================================================================
_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.S)


def parse_verdict(content, expected_items):
    """Turn the judge's reply into a verdict. NEVER raise.

    A judge that answers in prose, wraps its JSON in a fence, or emits
    six verdicts for five items has not graded the case - so the case
    fails, and the reason says exactly what went wrong. Defaulting to
    PASS here would let an unparseable answer inflate the pass rate,
    which is the one direction an evaluation harness must never round.
    """
    text = (content or "").strip()
    if not text:
        return False, [], "judge returned an empty response"

    blob = text
    fenced = _FENCE.search(text)
    if fenced:
        blob = fenced.group(1)
    else:
        start, end = blob.find("{"), blob.rfind("}")
        if start != -1 and end > start:
            blob = blob[start:end + 1]

    try:
        data = json.loads(blob)
    except (ValueError, TypeError) as err:
        return False, [], "judge returned malformed JSON (%s): %.120s" % (
            err, text.replace("\n", " "))

    if not isinstance(data, dict):
        return False, [], "judge returned %s, expected an object" % type(data).__name__

    items = data.get("items")
    if not isinstance(items, list):
        return False, [], "judge response has no `items` list"

    clean, absent = [], []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        verdict = str(entry.get("verdict", "")).strip().lower()
        if verdict not in ("present", "absent"):
            return False, [], ("judge used verdict %r; only 'present' and "
                               "'absent' are allowed" % entry.get("verdict"))
        clean.append({"item": entry.get("item"), "verdict": verdict,
                      "evidence": entry.get("evidence")})
        if verdict == "absent":
            absent.append(str(entry.get("item"))[:60])

    if len(clean) != len(expected_items):
        return False, clean, ("judge ruled on %d item(s), %d were required"
                              % (len(clean), len(expected_items)))

    # `pass` is DERIVED, not trusted. The judge is asked for it, and the
    # ask is what makes it think item by item - but a model that marks
    # three items absent and then writes "pass": true has contradicted
    # itself, and the items are the evidence.
    passed = not absent
    reason = (str(data.get("reason") or "")[:200] if passed
              else "absent: %s" % "; ".join(absent))
    return passed, clean, reason


# =====================================================================
# THE PUBLIC FUNCTION
# =====================================================================
def evaluate_outcome(expected, actual, judge_model=None, doc=None):
    """Judge ONE queue item. Returns a dict; never raises on a bad reply.

    `expected` is the answer-key row (or just its must_record list).
    `actual`   is the judgement_queue item for that case.

    Returns {passed, items, reason, graded_by, usage, error}.
    """
    judge_model = judge_model or DEFAULT_JUDGE_MODEL
    with open(PROMPT_PATH, encoding="utf-8") as fh:
        template = fh.read()

    item = dict(actual)
    if isinstance(expected, dict) and expected.get("must_record"):
        item.setdefault("must_record", expected["must_record"])
    required = item.get("must_record") or []

    messages = [
        {"role": "system",
         "content": render_prompt(template, item, doc or {},
                                  (expected or {}).get("expected_decision")
                                  if isinstance(expected, dict) else None)},
        {"role": "user",
         "content": "Rule on each required item now. JSON only."},
    ]

    saved_model, saved_cap = config.MODEL, config.MAX_TOKENS_PER_CALL
    try:
        config.MODEL = judge_model
        config.MAX_TOKENS_PER_CALL = JUDGE_MAX_TOKENS
        content, usage, meta = LIVE_CALL(messages)
    except LiveFatalError:
        raise                                   # a bad key or model id: stop
    except LiveTransportError as err:
        return {"passed": False, "items": [], "usage": {},
                "reason": "transport failure after retries: %s" % err,
                "graded_by": "model: %s" % judge_model, "error": "transport"}
    finally:
        config.MODEL, config.MAX_TOKENS_PER_CALL = saved_model, saved_cap

    passed, items, reason = parse_verdict(content, required)
    return {"passed": passed, "items": items, "reason": reason,
            "graded_by": "model: %s" % judge_model,
            "served_model": (meta or {}).get("served_model"),
            "usage": usage or {}, "error": None if items else "parse"}


# =====================================================================
# THE TWO PATHS
# =====================================================================
def judge_by_person(queue, who):
    tokens_in = tokens_out = 0
    for n, item in enumerate(queue, 1):
        required = item.get("must_record") or []
        print("\n" + "=" * 68)
        print("  %d of %d · %s · decided %s"
              % (n, len(queue), item["case_id"], item.get("decision")))
        print("=" * 68)
        print("  REASON GIVEN:\n    %s\n" % (item.get("reason") or "(none)"))
        verdicts, absent = [], []
        for m in required:
            answer = ""
            while answer not in ("y", "n"):
                answer = input("    present? [y/n]  %s\n    > " % m).strip().lower()
            verdicts.append({"item": m,
                             "verdict": "present" if answer == "y" else "absent",
                             "evidence": "ruled by %s" % who})
            if answer == "n":
                absent.append(m[:60])
        item["verdict"] = "pass" if not absent else "fail"
        item["items"] = verdicts
        item["graded_by"] = "person: %s" % who
        item["judge_reason"] = ("all %d item(s) present" % len(required)
                                if not absent else
                                "absent: %s" % "; ".join(absent))
    return tokens_in, tokens_out


def judge_by_model(queue, doc, judge_model, key_map, spend_cap):
    tokens_in = tokens_out = 0
    spent = 0.0
    for n, item in enumerate(queue, 1):
        expected = key_map.get(item["case_id"], {})
        out = evaluate_outcome(expected, item, judge_model, doc)

        item["verdict"] = "pass" if out["passed"] else "fail"
        item["items"] = out["items"]
        item["graded_by"] = out["graded_by"]
        item["judge_reason"] = out["reason"]
        if out.get("error"):
            item["judge_error"] = out["error"]

        u = out.get("usage") or {}
        ti = int(u.get("prompt_tokens") or 0)
        to = int(u.get("completion_tokens") or 0)
        tokens_in += ti
        tokens_out += to
        spent = (tokens_in / 1e6) * config.PRICE_IN + (tokens_out / 1e6) * config.PRICE_OUT

        print("  %3d/%d  %-12s %-5s  %s"
              % (n, len(queue), item["case_id"], item["verdict"].upper(),
                 (out["reason"] or "")[:70]))

        if spent > spend_cap:
            print("\n  STOPPING: judged spend US$%.4f passed the cap of US$%.2f."
                  % (spent, spend_cap))
            print("  %d of %d item(s) graded. The rest stay PENDING and the"
                  % (n, len(queue)))
            print("  judged file below records that honestly.\n")
            break
    return tokens_in, tokens_out


# =====================================================================
# USAGE ACCOUNTING  (a D6 input, written not printed)
# =====================================================================
def write_usage(judge_model, graded_file, judged, tokens_in, tokens_out):
    os.makedirs(JUDGE_USAGE_DIR, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    slug = judge_model.replace("/", "-").replace(":", "-")
    path = os.path.join(JUDGE_USAGE_DIR,
                        "judge_usage__%s__%s.json" % (slug, stamp))
    cost = (tokens_in / 1e6) * config.PRICE_IN + (tokens_out / 1e6) * config.PRICE_OUT
    doc = {
        "judge_model": judge_model,
        "graded_file": os.path.relpath(graded_file, ROOT),
        "judge_prompt_sha256": prompt_sha256(),
        "items_judged": judged,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "price_in_per_million": config.PRICE_IN,
        "price_out_per_million": config.PRICE_OUT,
        "cost_usd": round(cost, 6),
        "date": stamp,
        "note": ("live spend OUTSIDE the D5(b) battery - it does not pass "
                 "through run_battery, so D6 must add this file as an input "
                 "or it under-reports the OpenRouter bill"),
    }
    body = json.dumps(doc, indent=2)
    key = config.api_key()
    if key and key in body:                       # belt and braces
        raise SystemExit("  REFUSING TO WRITE: the key appears in the output.")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")
    return path, cost


# =====================================================================
# MAIN
# =====================================================================
def main(argv=None):
    ap = argparse.ArgumentParser(prog="judge.py")
    ap.add_argument("results", help="a results JSON written by run_eval.py")
    ap.add_argument("--by", choices=["person", "model"], default="person")
    ap.add_argument("--model", default=DEFAULT_JUDGE_MODEL,
                    help="judge model id (cheap tier; must differ from the "
                         "model being graded)")
    ap.add_argument("--limit", type=int,
                    help="judge only the first N items - use this to verify "
                         "the wiring before spending on all of them")
    ap.add_argument("--spend-cap", type=float, default=JUDGE_SPEND_CAP_USD)
    ap.add_argument("--allow-dotenv", action="store_true",
                    help="fall back to reading OPENROUTER_API_KEY from .env. "
                         "Off by default: see GUARDRAILS.md 4.4")
    ap.add_argument("--name", help="who is judging, for --by person")
    args = ap.parse_args(argv)

    doc = load_results(args.results)
    queue = doc.get("judgement_queue") or []
    if not queue:
        print("\n  %s has an empty judgement_queue. Nothing to judge.\n"
              % args.results)
        return 1

    from evals.harness import load_key
    key_rows = load_key(doc.get("problem"))
    key_map = ({r["case_id"]: r for r in key_rows} if isinstance(key_rows, list)
               else key_rows)

    if args.limit:
        queue = queue[:args.limit]

    print()
    print("=" * 68)
    print("  D4 · THE JUDGEMENT CHECK")
    print("=" * 68)
    print("  results file    %s" % os.path.relpath(args.results, ROOT))
    print("  graded model    %s" % (doc.get("model") or doc.get("backend")))
    print("  items to judge  %d" % len(queue))
    print("  judged by       %s" % (args.by if args.by == "person"
                                    else "model: %s" % args.model))
    print("  judge prompt    sha %s" % prompt_sha256()[:12])

    tokens_in = tokens_out = 0
    if args.by == "model":
        refuse_self_grading(doc, args.model)
        if not resolve_key(args.allow_dotenv):
            print("\n  NO API KEY. This path spends money and needs one.\n"
                  "    OPENROUTER_API_KEY=sk-or-... python3 %s %s --by model\n"
                  "  Or judge for free:  python3 %s %s --by person\n"
                  % (sys.argv[0], args.results, sys.argv[0], args.results))
            return 2
        install_scrubbing_excepthook(resolve_key(args.allow_dotenv))
        print("  spend cap       US$%.2f   (judging is NOT the experiment)"
              % args.spend_cap)
        print("=" * 68)
        print()
        try:
            tokens_in, tokens_out = judge_by_model(queue, doc, args.model,
                                                   key_map, args.spend_cap)
        except LiveFatalError as err:
            # Retrying will not fix any of these, so say which one it is
            # and what to do about it. A stack trace through urllib tells
            # the reader nothing they can act on.
            print("\n  THE JUDGE COULD NOT RUN.  %s\n" % err)
            if "401" in str(err) or "key" in str(err).lower():
                print("  OpenRouter rejected the key. Check that it is current")
                print("  and starts 'sk-or-'. Nothing was judged and nothing")
                print("  was spent.")
            elif "404" in str(err):
                print("  OpenRouter does not know the model id %r." % args.model)
                print("  Check the exact slug on openrouter.ai/models - they")
                print("  change. Nothing was judged and nothing was spent.")
            elif "402" in str(err):
                print("  The key is out of credit. Nothing was judged.")
            print("\n  The free path needs no key at all:")
            print("      python3 %s %s --by person\n"
                  % (os.path.relpath(__file__, ROOT), args.results))
            return 2
    else:
        who = args.name or input("  your name: ").strip() or "unnamed"
        print("=" * 68)
        judge_by_person(queue, who)

    # ---- write the judged copy; never touch the input ----------------
    out_path = (args.results if args.results.endswith("__judged.json")
                else args.results.replace(".json", "__judged.json"))
    judged = [q for q in (doc.get("judgement_queue") or []) if q.get("verdict")]
    doc["judgement"] = {
        "judged_by": ("model: %s" % args.model if args.by == "model"
                      else "person"),
        "judge_prompt_sha256": prompt_sha256(),
        "items_total": len(doc.get("judgement_queue") or []),
        "items_judged": len(judged),
        "items_pending": len(doc.get("judgement_queue") or []) - len(judged),
        "passed": sum(1 for q in judged if q["verdict"] == "pass"),
        "failed": sum(1 for q in judged if q["verdict"] == "fail"),
        "judge_tokens_in": tokens_in,
        "judge_tokens_out": tokens_out,
        "date": datetime.date.today().isoformat(),
    }
    body = json.dumps(doc, indent=2, default=str)
    key = config.api_key()
    if key and key in body:
        raise SystemExit("  REFUSING TO WRITE: the key appears in the output.")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(body)

    s = doc["judgement"]
    print()
    print("=" * 68)
    print("  %d judged · %d pass · %d fail · %d PENDING"
          % (s["items_judged"], s["passed"], s["failed"], s["items_pending"]))
    if s["items_pending"]:
        print("  %d case(s) not yet judged. Do not quote a judgement rate"
              % s["items_pending"])
        print("  that includes them - PENDING is neither a pass nor a fail.")
    print("=" * 68)
    print("  Wrote %s" % os.path.relpath(out_path, ROOT))

    if args.by == "model" and (tokens_in or tokens_out):
        path, cost = write_usage(args.model, args.results, s["items_judged"],
                                 tokens_in, tokens_out)
        print("  Judge spend  %d in / %d out tokens · US$%.5f"
              % (tokens_in, tokens_out, cost))
        print("  Wrote %s" % os.path.relpath(path, ROOT))
        print("  ^ a D6 INPUT. This spend is outside the D5(b) battery and")
        print("    will not appear in logs/battery/ - add it or the cost")
        print("    model under-reports the real bill.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
