#!/usr/bin/env python3
"""
PE6201 · A2 — REHEARSE THE JUDGE WITHOUT A KEY OR A DOLLAR  (D4)
====================================================================
    python3 evals/graders/test_judge_fake.py

Free, offline, deterministic. Rebinds backends.LIVE_CALL to a fake that
returns the reply shapes a real judge actually produces - clean JSON, a
markdown fence, prose with JSON buried in it, an outright refusal to
answer in JSON at all - and checks the grader survives every one.

WHY THIS FILE EXISTS. The judge is a MEASURING INSTRUMENT, and an
instrument nobody has tested is a number nobody should quote. The two
failure modes that matter both produce a plausible-looking pass rate:

  * a malformed reply silently counted as a PASS  - inflates the rate
  * a whole case silently skipped                 - shrinks the
    denominator, which inflates it again

Both are checked below. Following test_battery_fake.py's pattern: every
failure mode rehearsed before any of them costs money.
====================================================================
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config                                      # noqa: E402
from backends import backends                      # noqa: E402
from evals.graders import judge                    # noqa: E402
from evals.graders import code_check as ck         # noqa: E402

PASSED, FAILED = [], []


def check(label, condition, detail=""):
    (PASSED if condition else FAILED).append(label)
    print("  %s  %s%s" % ("PASS" if condition else "FAIL", label,
                          "" if condition else "   <- %s" % detail))


def items_from_prompt(system_message):
    """Read the REQUIRED ITEMS array back out of the rendered prompt.

    A real judge has to do exactly this, so if the fake cannot, the
    prompt is ambiguous - which is how this test found that the items
    used to render as a numbered list directly above a numbered list of
    output rules. The first version of this fake returned 15 verdicts
    for 5 items, and it was the PROMPT that was wrong, not the fake.
    """
    tail = system_message.split("REQUIRED ITEMS", 1)[1]
    blob = tail[tail.index("```json") + len("```json"):]
    return json.loads(blob[:blob.index("```")].strip())


# =====================================================================
# 1 · THE PARSER, against the shapes a real model emits
# =====================================================================
def test_parser():
    print("\n  1 · PARSING WHAT A REAL JUDGE ACTUALLY SENDS BACK")
    want = ["item one", "item two"]

    def reply(pairs, overall=None):
        body = {"items": [{"item": i, "verdict": v, "evidence": "e"}
                          for i, v in pairs]}
        if overall is not None:
            body["pass"] = overall
        body["reason"] = "graded"
        return json.dumps(body)

    ok, _, _ = judge.parse_verdict(
        reply([("item one", "present"), ("item two", "present")], True), want)
    check("clean JSON with every item present -> pass", ok is True)

    ok, _, why = judge.parse_verdict(
        reply([("item one", "present"), ("item two", "absent")], False), want)
    check("one absent item -> fail, and names it", ok is False and "item two" in why)

    fenced = "```json\n%s\n```" % reply(
        [("item one", "present"), ("item two", "present")], True)
    ok, _, _ = judge.parse_verdict(fenced, want)
    check("markdown-fenced JSON is unwrapped", ok is True)

    chatty = "Sure! Here is my assessment:\n%s\nHope that helps." % reply(
        [("item one", "present"), ("item two", "present")], True)
    ok, _, _ = judge.parse_verdict(chatty, want)
    check("JSON buried in prose is recovered", ok is True)

    # THE ONE THAT MATTERS MOST. An unparseable reply must never pass.
    for label, raw in (("malformed JSON", '{"items": [ oops'),
                       ("empty response", ""),
                       ("prose only", "Both items look fine to me."),
                       ("a JSON list, not an object", '[1, 2, 3]'),
                       ("no items key", '{"pass": true}')):
        ok, _, why = judge.parse_verdict(raw, want)
        check("%s -> FAIL, not pass" % label, ok is False, why)

    ok, _, why = judge.parse_verdict(
        reply([("item one", "maybe"), ("item two", "present")]), want)
    check("an invented verdict word is refused", ok is False and "maybe" in why)

    ok, _, why = judge.parse_verdict(reply([("item one", "present")]), want)
    check("too few verdicts -> fail, with the count", ok is False and "1 item" in why)

    # A judge that marks an item absent and then claims "pass": true has
    # contradicted itself. The ITEMS are the evidence; `pass` is derived.
    ok, _, _ = judge.parse_verdict(
        reply([("item one", "absent"), ("item two", "present")], True), want)
    check("`pass: true` is NOT trusted over an absent item", ok is False)


# =====================================================================
# 2 · THE CHECK-KIND CLASSIFIER
# =====================================================================
def test_classifier():
    print("\n  2 · WHICH CHECK GRADES WHICH FIELD  (D4)")
    esc = {"case_id": "X", "expected_decision": "escalate",
           "trigger": "policy_lapsed", "must_record": ["a", "b"]}
    req = {"case_id": "Y", "expected_decision": "request_document",
           "missing": "itemised bill for line 45378", "must_record": ["a"]}
    plain = {"case_id": "Z", "expected_decision": "approve_in_principle"}

    check("decision is always a code check",
          all("decision" in ck.check_kinds(r)["code"] for r in (esc, req, plain)))
    check("trigger is a code check when present",
          "trigger" in ck.check_kinds(esc)["code"])
    check("missing is a code check when present",
          "missing" in ck.check_kinds(req)["code"])
    check("must_record is NEVER a code check",
          all("must_record" not in ck.check_kinds(r)["code"]
              for r in (esc, req, plain)))
    check("must_record is a judgement check",
          ck.check_kinds(esc)["judgement"] == ["must_record"])
    check("label reads code+judgement", ck.check_kind_label(esc) == "code+judgement")
    check("label reads code alone with no prose",
          ck.check_kind_label(plain) == "code")


# =====================================================================
# 3 · THE WHOLE PATH, with a fake model
# =====================================================================
def test_end_to_end(tmp_dir):
    print("\n  3 · THE WHOLE JUDGING PASS, NO KEY AND NO NETWORK")
    src = os.path.join(ROOT, "results", "scripted")
    files = sorted(f for f in os.listdir(src) if f.startswith("problemA__scripted"))
    if not files:
        check("a scripted results file exists to judge", False,
              "run `python3 run_eval.py` first")
        return
    with open(os.path.join(src, files[-1]), encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["model"] = "some/graded-model"
    path = os.path.join(tmp_dir, "judge_test_results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)

    calls = {"n": 0, "prompts": []}

    def fake(messages):
        calls["n"] += 1
        sysmsg = messages[0]["content"]
        calls["prompts"].append(sysmsg)
        items = items_from_prompt(sysmsg)
        if calls["n"] == 2:                       # a judge that ignores the format
            return "Looks fine to me honestly.", {"prompt_tokens": 800,
                                                  "completion_tokens": 9}, {}
        verdicts = [{"item": it,
                     "verdict": "absent" if (calls["n"] == 3 and i == 0)
                                else "present",
                     "evidence": "the record says so"}
                    for i, it in enumerate(items)]
        return (json.dumps({"items": verdicts,
                            "pass": all(v["verdict"] == "present" for v in verdicts),
                            "reason": "graded"}),
                {"prompt_tokens": 1200, "completion_tokens": 90},
                {"served_model": "fake/judge"})

    real = backends.LIVE_CALL
    backends.LIVE_CALL, judge.LIVE_CALL = fake, fake
    config.set_api_key("sk-or-FAKE-never-leaves-memory")
    try:
        rc = judge.main([path, "--by", "model", "--model", "fake/judge-model",
                         "--limit", "4"])
    finally:
        backends.LIVE_CALL, judge.LIVE_CALL = real, real
        config.set_api_key(None)

    check("the judging pass exits 0", rc == 0, "rc=%s" % rc)
    check("one call per case, not per item", calls["n"] == 4, "n=%d" % calls["n"])

    p0 = calls["prompts"][0]
    check("prompt renders {actual_trajectory}", "tool calls:" in p0)
    check("prompt renders {reason}", "{reason}" not in p0)
    check("prompt renders {expected_outcome}", "{expected_outcome}" not in p0)
    check("prompt leaves no unfilled placeholder", "{must_record}" not in p0)
    check("required items render as a JSON array",
          isinstance(items_from_prompt(p0), list))

    judged_path = path.replace(".json", "__judged.json")
    check("wrote <input>__judged.json", os.path.isfile(judged_path))
    with open(path, encoding="utf-8") as fh:
        check("the INPUT file was not modified",
              json.load(fh)["judgement_queue"][0]["verdict"] is None)

    with open(judged_path, encoding="utf-8") as fh:
        out = json.load(fh)
    s = out["judgement"]
    q = out["judgement_queue"]

    check("summary counts the judged items", s["items_judged"] == 4,
          str(s["items_judged"]))
    check("unjudged items stay PENDING, not failed",
          s["items_pending"] == len(q) - 4, str(s["items_pending"]))
    check("judged + pending == total",
          s["items_judged"] + s["items_pending"] == s["items_total"])
    check("the malformed reply was recorded as a FAIL",
          q[1]["verdict"] == "fail" and "malformed" in q[1]["judge_reason"],
          q[1].get("judge_reason", ""))
    check("a genuine absent item fails its case", q[2]["verdict"] == "fail")
    check("clean replies pass", q[0]["verdict"] == "pass" and q[3]["verdict"] == "pass")
    check("graded_by names the judge model",
          q[0]["graded_by"] == "model: fake/judge-model")
    check("per-item verdicts are kept, not just the case verdict",
          isinstance(q[0].get("items"), list) and len(q[0]["items"]) > 0)
    check("the prompt sha is recorded with the verdicts",
          len(s.get("judge_prompt_sha256", "")) == 64)
    check("MEASURED judge tokens are recorded",
          s["judge_tokens_in"] > 0 and s["judge_tokens_out"] > 0)
    check("pending items are NOT counted as passes",
          s["passed"] + s["failed"] == s["items_judged"])

    body = json.dumps(out)
    check("the key never reaches the judged file",
          "sk-or-FAKE-never-leaves-memory" not in body)
    check("nothing key-shaped reaches the judged file", "sk-or-" not in body)

    usage = os.path.join(ROOT, "results", "judge",
                         "judge_usage__fake-judge-model__%s.json"
                         % out["judgement"]["date"])
    check("wrote the D6 judge-usage file", os.path.isfile(usage))
    if os.path.isfile(usage):
        with open(usage, encoding="utf-8") as fh:
            u = json.load(fh)
        check("usage file carries measured tokens and a cost",
              u["tokens_in"] > 0 and u["cost_usd"] > 0)
        check("usage file names the judge model", u["judge_model"] == "fake/judge-model")
        check("the key never reaches the usage file", "sk-or-" not in json.dumps(u))
        os.remove(usage)


# =====================================================================
# 4 · THE REFUSALS
# =====================================================================
def test_refusals():
    print("\n  4 · WHAT IT REFUSES TO DO")
    try:
        judge.refuse_self_grading({"model": "a/b"}, "a/b")
        check("a model may not grade its own results", False, "it allowed it")
    except SystemExit:
        check("a model may not grade its own results", True)
    try:
        judge.refuse_self_grading({"model": "a/b"}, "c/d")
        check("a different judge model is allowed", True)
    except SystemExit:
        check("a different judge model is allowed", False)

    check("the default judge is a cheap-tier model",
          judge.DEFAULT_JUDGE_MODEL in (
              "meta-llama/llama-3.1-8b-instruct", "google/gemini-flash-1.5"),
          judge.DEFAULT_JUDGE_MODEL)
    check("judging carries its own spend cap", judge.JUDGE_SPEND_CAP_USD <= 1.0)
    check("judge completions are capped below an agent turn",
          judge.JUDGE_MAX_TOKENS < config.MAX_TOKENS_PER_CALL)

    roster = os.path.join(ROOT, "evals", "battery_roster.json")
    if os.path.isfile(roster):
        with open(roster, encoding="utf-8") as fh:
            models = {m.get("model") for m in json.load(fh).get("members", [])}
        check("the default judge is not on the battery roster",
              judge.DEFAULT_JUDGE_MODEL not in models,
              "it would grade a teammate's own run")


def main():
    import tempfile
    print()
    print("=" * 70)
    print("  REHEARSING THE D4 JUDGE - free, offline, no key")
    print("=" * 70)
    test_parser()
    test_classifier()
    with tempfile.TemporaryDirectory() as tmp:
        test_end_to_end(tmp)
    test_refusals()
    print()
    print("=" * 70)
    print("  %d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        for f in FAILED:
            print("    FAILED: %s" % f)
    else:
        print("  Every judge failure mode rehearsed. Safe to spend on it.")
    print("=" * 70)
    print()
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
