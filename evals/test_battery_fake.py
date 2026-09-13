#!/usr/bin/env python3
"""
PE6201 · A2 — THE BATTERY, EXERCISED WITHOUT A KEY  (D5b)
====================================================================
    python3 evals/test_battery_fake.py

Every failure mode the live battery can hit, rehearsed against a fake
vendor. No network, no key, no cost.

WHY THIS EXISTS. The battery spends real money from a US$10 key that
also has to cover the End-of-Course Project, and it spends it sixty
calls at a time. Discovering that the retry logic is wrong, or that
resume loses the file, or that the key leaks into the results, is worth
finding out for free beforehand rather than at trial 45 of 60.

The seam is one line in backends.py: `LIVE_CALL = _live_call`. Rebinding
it here means the loop, the guardrails, the gate, the ledger, the
checkpoint, the budget and the provenance layer all run exactly as they
will on the day - only the vendor is imaginary.

No pytest: this repository has no test framework and requirements.txt is
empty. Plain asserts and a printed table, runnable by anyone.
====================================================================
"""
import json
import os
import sys
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config                                          # noqa: E402
from backends import backends                          # noqa: E402
from backends import planner                           # noqa: E402
from evals import battery_checkpoint as ckpt           # noqa: E402
from evals import battery_provenance as prov           # noqa: E402
from evals import run_battery as rb                    # noqa: E402

PASSED, FAILED = [], []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(name)
    print("  %s  %s%s" % ("PASS" if condition else "FAIL", name,
                          ("   " + detail) if detail and not condition else ""))


# =====================================================================
# THE FAKE VENDOR
# =====================================================================
class Fake(object):
    """Replays the planner's moves as if a model had produced them.

    Using the planner rather than hand-written JSON means the fake
    exercises the SAME move shapes the real thing will see - multi-call
    turns, the gated action, early exits - instead of a happy path
    invented to make the test pass.
    """

    def __init__(self):
        self.case, self.turn = None, 0
        self.usage = {"prompt_tokens": 1200, "completion_tokens": 90}
        self.meta = {"served_model": None, "provider": "FakeProvider"}
        self.script = None          # override the content entirely
        self.raise_seq = []         # exceptions to raise, in order
        self.calls = 0
        self.seen = []              # every `messages` list, for inspection

    def __call__(self, messages):
        self.calls += 1
        self.seen.append([dict(m) for m in messages])
        if self.raise_seq:
            err = self.raise_seq.pop(0)
            if err is not None:
                raise err
        if self.script is not None:
            return self.script, dict(self.usage), dict(self.meta)
        moves = planner.plan(self.case, "parallel")
        move = moves[self.turn] if self.turn < len(moves) else moves[-1]
        self.turn += 1
        return json.dumps(move, default=str), dict(self.usage), dict(self.meta)


FAKE = Fake()


def install_fake():
    backends.LIVE_CALL = FAKE
    original_init = backends.LiveBackend.__init__

    def init(self, case_id, tool_descriptors, system_prompt):
        original_init(self, case_id, tool_descriptors, system_prompt)
        FAKE.case, FAKE.turn = case_id, 0

    backends.LiveBackend.__init__ = init
    backends.time.sleep = lambda _s: None      # do not really back off


def live_mode():
    config.RUNTIME_OVERRIDE = True
    config.BACKEND = "live"
    config.MODEL = "fake/model-a"
    config.set_api_key("sk-or-FAKEKEY0000")
    FAKE.meta["served_model"] = "fake/model-a"


def http_error(code, retry_after=None):
    hdrs = {"Retry-After": retry_after} if retry_after else {}
    return urllib.error.HTTPError("http://x", code, "err", hdrs, None)


# ---------------------------------------------------------------------
# THE SECOND SEAM, AND WHY IT IS NEEDED.
#
# Rebinding LIVE_CALL replaces _live_call ENTIRELY - including the retry
# logic that lives inside it. So the transport scenarios below fake at
# the HTTP layer instead, leaving the real _live_call in place. Testing
# retry through a fake that has no retry would prove nothing, and that is
# exactly the kind of test that passes while the system is broken.
# ---------------------------------------------------------------------
class _Resp(object):
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self, *a):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_http(sequence):
    """`sequence` is a list of exceptions-or-None, consumed per call."""
    seq = list(sequence)

    def urlopen(req, timeout=None):
        item = seq.pop(0) if seq else None
        if isinstance(item, Exception):
            raise item
        moves = planner.plan(FAKE.case, "parallel")
        move = moves[FAKE.turn] if FAKE.turn < len(moves) else moves[-1]
        FAKE.turn += 1
        return _Resp({"choices": [{"message": {"content":
                                               json.dumps(move, default=str)}}],
                      "usage": dict(FAKE.usage),
                      "model": "fake/model-a", "provider": "FakeProvider"})
    return urlopen


def with_real_transport(sequence):
    """Restore the real _live_call and fake only the socket underneath."""
    backends.LIVE_CALL = backends._live_call
    backends.urllib.request.urlopen = fake_http(sequence)


def with_fake_call():
    backends.LIVE_CALL = FAKE


# =====================================================================
# THE SCENARIOS
# =====================================================================
def scenario_happy():
    from loop_agent import run_case
    FAKE.raise_seq, FAKE.script = [], None
    rec = run_case("CLM-8842", problem="A")
    check("1  live path produces a decision",
          rec["decision"] == "approve_in_principle", rec.get("decision"))
    check("1b measured tokens are the fake's, not an estimate",
          rec["tokens_in"] == 1200 * len(rec["turn_tokens"]),
          str(rec["tokens_in"]))
    # turns + 1: the concluding move is a billed call like any other.
    check("1c per-turn tokens recorded, including the concluding call",
          len(rec["turn_tokens"]) == rec["turns"] + 1,
          "%d entries for %d turns" % (len(rec["turn_tokens"]), rec["turns"]))
    check("1d served model + provider captured",
          rec.get("served_model") == "fake/model-a"
          and rec.get("provider") == "FakeProvider")
    # cost must follow the ROSTER price, not the cheap-tier default
    config.PRICE_IN, config.PRICE_OUT = 1.00, 5.00
    rec2 = run_case("CLM-8842", problem="A")
    expect = rec2["tokens_in"] / 1e6 * 1.00 + rec2["tokens_out"] / 1e6 * 5.00
    check("1e cost uses the per-member price",
          abs(rec2["cost_usd"] - round(expect, 6)) < 1e-6)
    config.PRICE_IN, config.PRICE_OUT = 0.10, 0.40


def scenario_retry():
    """The REAL retry code, with only the socket faked."""
    from loop_agent import run_case
    with_real_transport([http_error(429, "0"), http_error(503)]
                        + [None] * 40)
    rec = run_case("CLM-8842", problem="A")
    check("2  the real retry survives a 429 then a 503",
          rec["decision"] == "approve_in_principle", str(rec.get("decision")))
    with_fake_call()


def scenario_fatal():
    """401/402/404 must abort on the FIRST call. Sixty exponential
    backoffs against a typo'd model id is a forty-minute failure where a
    thirty-second one was available."""
    from loop_agent import run_case
    for code, label in ((401, "3  401 (bad key) aborts on the first call"),
                        (402, "4  402 (no credits) aborts on the first call"),
                        (404, "4b 404 (unknown model id) aborts immediately")):
        calls = {"n": 0}
        seq = [http_error(code)] * 30

        def counting(req, timeout=None, _seq=seq, _c=calls):
            _c["n"] += 1
            raise _seq.pop(0)

        backends.LIVE_CALL = backends._live_call
        backends.urllib.request.urlopen = counting
        try:
            run_case("CLM-8842", problem="A")
            check(label, False, "no exception raised")
        except backends.LiveFatalError:
            check(label, calls["n"] == 1, "made %d calls" % calls["n"])
        except Exception as err:                          # noqa: BLE001
            check(label, False, type(err).__name__)
    with_fake_call()


def scenario_transport_exhausted():
    from loop_agent import run_case
    with_real_transport([http_error(503)] * (config.RETRY_MAX + 5))
    rec = run_case("CLM-8842", problem="A")
    check("5  exhausted retries -> stopped_by 'transport', not a crash",
          rec.get("stopped_by") == "transport", str(rec.get("stopped_by")))
    check("5b transport trials are excluded from the denominator",
          rb.aggregate([{"case_id": "X", "trial": 1, "passed": False,
                         "record": rec}],
                       {"X": {"expected_decision": "escalate"}})["trials_graded"] == 0)
    with_fake_call()


def scenario_unparseable():
    from loop_agent import run_case
    FAKE.script = "I am a helpful assistant and this is not JSON."
    rec = run_case("CLM-8842", problem="A")
    check("6  unparseable output degrades loudly, does not crash",
          rec["decision"] == "escalate" and "JSON" in rec.get("reason", ""))
    FAKE.script = None


def scenario_usage_missing():
    from loop_agent import run_case
    saved = FAKE.usage
    FAKE.usage = {}
    rec = run_case("CLM-8842", problem="A")
    check("7  a missing usage block is flagged, not silently free",
          rec.get("usage_complete") is False and rec["cost_usd"] == 0.0)
    FAKE.usage = saved


def scenario_reasoning():
    from loop_agent import run_case
    saved = FAKE.usage
    FAKE.usage = {"prompt_tokens": 1200, "completion_tokens": 40000,
                  "completion_tokens_details": {"reasoning_tokens": 39000}}
    rec = run_case("CLM-8842", problem="A")
    spike = rb.detect_reasoning(rec, 90)
    check("8  a reasoning model is detected from the record",
          spike is not None and "reasoning" in spike)
    halts = []
    budget = rb.Budget(100.0)
    run_one = rb.make_run_one(budget, {"member": "t"}, 90,
                              lambda w, d: halts.append((w, d)))
    try:
        run_one("CLM-8842", problem="A")
        check("8b reasoning halts the battery", False, "no halt")
    except rb.BatteryHalt:
        check("8b reasoning halts the battery", halts and halts[0][0] == "reasoning")
    FAKE.usage = saved


def scenario_budget():
    halts = []
    budget = rb.Budget(0.0001)
    run_one = rb.make_run_one(budget, {"member": "t"}, None,
                              lambda w, d: halts.append((w, d)))
    try:
        run_one("CLM-8842", problem="A")
        check("9  the spend cap halts on MEASURED cost", False, "no halt")
    except rb.BatteryHalt:
        check("9  the spend cap halts on MEASURED cost",
              halts and halts[0][0] == "max_spend")


def scenario_exception_isolation():
    halts = []
    budget = rb.Budget(100.0)
    run_one = rb.make_run_one(budget, {"member": "t"}, None,
                              lambda w, d: halts.append((w, d)))
    rec = run_one("CLM-NOT-A-CASE", problem="A")
    check("10 one broken trial does not end the battery",
          rec.get("stopped_by") in ("exception", None)
          and rec.get("decision") == "escalate")


# ---- provenance ------------------------------------------------------
def scenario_roster_rules():
    base = prov.load_roster()

    def errs(mutate):
        r = json.loads(json.dumps(base))
        mutate(r)
        return prov.validate_roster(r, today=None)

    def same_family(r):
        r["members"][1]["family"] = r["members"][0]["family"]
    check("11 two v2 members in one family is refused",
          any("family" in e for e in errs(same_family)))

    def one_tier(r):
        for m in r["members"]:
            m["tier"] = "cheap"
    check("12 a single price tier is refused",
          any("tier" in e for e in errs(one_tier)))

    def v1_elsewhere(r):
        for m in r["members"]:
            if m["prompt_version"] == "v1":
                m["model"] = "some/other-model"
    check("13 a v1 pass on a model nobody ran is refused",
          any("holding the MODEL fixed" in e for e in errs(v1_elsewhere)))

    def two_v1(r):
        r["members"][0]["prompt_version"] = "v1"
    check("14 more than one v1 member is refused",
          any("exactly one member must run v1" in e for e in errs(two_v1)))


def scenario_derived_trials():
    fp = prov.fingerprint("A")
    shape = fp["plan_shape"]
    check("15 the trial count is DERIVED from the fixtures",
          shape["trials"] == shape["ordinary"] + 3 * shape["negative"],
          str(shape))
    roster = json.loads(json.dumps(prov.load_roster()))
    roster["trials_expected"] = shape["trials"] + 7
    v = prov.check_drift(fp, roster, roster["members"][0])
    check("15b a roster that disagrees with the data is refused",
          any(x.check == "trials_derived" for x in v))


def scenario_prompt_versions():
    fp = prov.fingerprint("A")
    check("16 v1 and v2 prompts differ",
          fp["prompt_sha256"]["v1"] != fp["prompt_sha256"]["v2"])
    roster = prov.load_roster()
    v1_member = next(m for m in roster["members"]
                     if m["prompt_version"] == "v1")
    v = prov.check_drift(fp, roster, v1_member)
    check("16b every Problem-A tool has a v1 descriptor",
          not any(x.check == "v1_descriptors_missing" for x in v),
          "DESCRIPTORS_V1 is complete")
    check("16c that refusal cannot be overridden",
          "v1_descriptors_missing" in prov.UNOVERRIDABLE)


def scenario_drift_detected():
    fp = prov.fingerprint("A")
    roster = json.loads(json.dumps(prov.load_roster()))
    roster["expected"]["answer_key_sha256"] = "0" * 64
    v = prov.check_drift(fp, roster, roster["members"][0])
    named = [x for x in v if x.check == "answer_key_sha256"]
    check("17 a moved answer key is caught AND named",
          bool(named) and named[0].fatal)


# ---- checkpoint ------------------------------------------------------
def scenario_checkpoint(tmp):
    path = os.path.join(tmp, "cp.jsonl")
    header = {"run_id": "aaa", "fingerprint": {"x": 1}}
    cp = ckpt.Checkpoint.open(path, header)
    for i in range(1, 4):
        cp.append({"kind": "trial", "case_id": "C%d" % i, "trial": 1,
                   "passed": True, "fails": [], "family": "f",
                   "record": {"cost_usd": 0.01}})
    cp.close()

    cp2 = ckpt.Checkpoint.open(path, header)
    check("18 resume sees completed trials", len(cp2.done()) == 3)
    check("18b resume sums the spend already made",
          abs(cp2.spend_usd() - 0.03) < 1e-9)
    cp2.close()

    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"kind": "trial", "case_id": "C4", "tri')   # killed mid-write
    cp3 = ckpt.Checkpoint.open(path, header)
    check("19 a truncated last line is dropped, not fatal",
          len(cp3.done()) == 3 and len(cp3.warnings) == 1)
    cp3.close()

    try:
        ckpt.Checkpoint.open(path, {"run_id": "bbb", "fingerprint": {"x": 2}})
        check("20 resuming a DIFFERENT experiment is refused", False)
    except ckpt.CheckpointConflict:
        check("20 resuming a DIFFERENT experiment is refused", True)

    cp4 = ckpt.Checkpoint.open(path, header)
    cp4.lock()
    try:
        cp4.lock()
        check("21 a second concurrent run is refused (no double spend)", False)
    except ckpt.Locked:
        check("21 a second concurrent run is refused (no double spend)", True)
    cp4.unlock()
    cp4.close()


def scenario_secret_never_written():
    key = "sk-or-REALLOOKINGKEY123"
    try:
        rb.assert_no_secret(json.dumps({"oops": key}), key)
        check("22 the key can never reach a results file", False)
    except SystemExit:
        check("22 the key can never reach a results file", True)
    try:
        rb.assert_no_secret(json.dumps({"note": "sk-or-anything"}), "other")
        check("22b anything key-SHAPED is refused too", False)
    except SystemExit:
        check("22b anything key-SHAPED is refused too", True)


def scenario_key_hygiene():
    out = os.path.join(ROOT, "results")
    hits = []
    for base, _d, files in os.walk(out):
        for f in files:
            try:
                if "sk-or-" in open(os.path.join(base, f),
                                    encoding="utf-8", errors="ignore").read():
                    hits.append(os.path.join(base, f))
            except OSError:
                pass
    check("23 no key-shaped string anywhere under results/", not hits,
          str(hits[:3]))


# =====================================================================
def scenario_transcript_fidelity():
    """THE CHECK THAT WOULD HAVE SAVED A LIVE BATTERY.

    On 2026-09-13 meta-llama/llama-3.1-8b-instruct scored 1/60, with 48
    trials halted by our own de-duplication guard on turn 2. The cause
    was here: the assistant turn carried only `thought`, so the model
    could not see the calls it had already made and re-issued them.

    The scripted backend CANNOT catch this - ScriptedBackend.next_move
    ignores `transcript` by design - so the assertion has to live in a
    fake-vendor test that inspects what was actually sent.
    """
    from loop_agent import run_case
    FAKE.seen = []
    FAKE.case, FAKE.turn = "CLM-8842", 0
    run_case("CLM-8842", problem="A")

    later = [m for m in FAKE.seen if len(m) > 1]
    check("24 the model is sent more than just a system prompt", bool(later))
    if not later:
        return
    msgs = later[-1]

    assistants = [m for m in msgs if m["role"] == "assistant"]
    check("24a the assistant turn REPLAYS the model's own calls",
          bool(assistants) and all("calls" in a["content"] for a in assistants),
          (assistants[0]["content"][:70] if assistants else "none"))

    bad = []
    for m in msgs[1:]:                      # skip the system prompt
        try:
            json.loads(m["content"])
        except (ValueError, TypeError):
            bad.append("%s: %s" % (m["role"], m["content"][:40]))
    check("24b every transcript entry is valid JSON, not repr()",
          not bad, "; ".join(bad[:2]))

    for a in assistants:
        payload = json.loads(a["content"])
        check("24c the replayed move keeps thought AND calls",
              "thought" in payload and isinstance(payload.get("calls"), list))
        break


def scenario_observation_truncation():
    """A cap that fires silently is a correctness bug wearing a cost
    bug's clothes. It has to reach guards.fired."""
    from loop_agent import run_case
    original = config.MAX_OBSERVATION_CHARS
    config.MAX_OBSERVATION_CHARS = 40       # forced far below any real result
    try:
        FAKE.seen = []
        FAKE.case, FAKE.turn = "CLM-8842", 0
        rec = run_case("CLM-8842", problem="A")
    finally:
        config.MAX_OBSERVATION_CHARS = original

    fired = [g["guardrail"] for g in rec.get("guardrails_fired", [])]
    check("25 an oversized observation is truncated AND recorded",
          "observation_truncated" in fired, str(fired))

    truncated_seen = any("truncated" in m["content"]
                         for msgs in FAKE.seen for m in msgs
                         if m["role"] == "user")
    check("25a the truncation is visible in the transcript, not hidden",
          truncated_seen)

    check("25b the real cap sits ABOVE every observation we emit, so it "
          "never fires on our data", config.MAX_OBSERVATION_CHARS >= 2000,
          str(config.MAX_OBSERVATION_CHARS))


def scenario_output_truncated():
    """finish_reason='length' is a severed reply, not a wrong answer, and
    must not be filed under 'did not return parseable JSON'."""
    from loop_agent import run_case
    FAKE.meta = dict(FAKE.meta, finish_reason="length")
    FAKE.script = '{"thought": "cut off mid-ob'      # severed JSON
    try:
        rec = run_case("CLM-8842", problem="A")
    finally:
        FAKE.script = None
        FAKE.meta.pop("finish_reason", None)

    check("26 a truncated completion is named, not mistaken for prose",
          rec.get("stopped_by") == "output_truncated", str(rec.get("stopped_by")))
    check("26a and it says so in the reason",
          "truncated" in (rec.get("reason") or "").lower(),
          (rec.get("reason") or "")[:60])


def main():
    import tempfile
    print()
    print("=" * 70)
    print("  THE LIVE BATTERY, REHEARSED AGAINST A FAKE VENDOR")
    print("  no network · no key · no cost")
    print("=" * 70)
    install_fake()
    live_mode()

    scenario_happy()
    scenario_retry()
    scenario_fatal()
    scenario_transport_exhausted()
    scenario_unparseable()
    scenario_usage_missing()
    scenario_reasoning()
    scenario_budget()
    scenario_exception_isolation()
    scenario_roster_rules()
    scenario_derived_trials()
    scenario_prompt_versions()
    scenario_drift_detected()
    with tempfile.TemporaryDirectory() as tmp:
        scenario_checkpoint(tmp)
    scenario_transcript_fidelity()
    scenario_observation_truncation()
    scenario_output_truncated()
    scenario_secret_never_written()
    scenario_key_hygiene()

    print()
    print("=" * 70)
    print("  %d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        for f in FAILED:
            print("    FAILED: %s" % f)
        print("\n  Do not run the live battery until these are green.")
    else:
        print("  Every failure mode rehearsed. Safe to fill the roster,")
        print("  cut the freeze tag, and spend.")
    print("=" * 70)
    print()
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
