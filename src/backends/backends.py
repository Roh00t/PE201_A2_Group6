"""
PE6201 · A2 scaffold — THE TWO BACKENDS
====================================================================
A backend answers ONE question: given the conversation so far, what
does the agent do next?

It returns either
    {"tool": "name", "args": {...}, "thought": "..."}      -> call a tool
    {"final": {...}, "thought": "..."}                     -> conclude

EXACTLY ONE FUNCTION IN THIS WHOLE REPOSITORY KNOWS A VENDOR EXISTS.
It is `_live_call` at the bottom. That is the D5 requirement, and it is
what makes swapping models a one-string change.

--------------------------------------------------------------------
WHY THE SCRIPTED BACKEND IS NOT A TOY

It replays a fixed sequence of decisions for a known case. That makes
your whole run deterministic, free, and reproducible by a stranger -
which is what D5(a) is marked on, and what makes D3(b) and D7 cost
nothing.

It is also the honest way to test your CODE. A guardrail either fires
or it does not; a model has no say in that. Scripting the model's
moves is how you test the parts you wrote.
====================================================================
"""
import json
import re
import random
import time
import urllib.error
import urllib.request

import config


class LiveTransportError(Exception):
    """A call failed for a reason that is not the model's fault and that
    retrying might have fixed - a 429, a 5xx, a dropped socket.

    It is a distinct type because loop_agent must treat it differently
    from a bad answer: the tokens already spent on turns 1..n-1 of this
    run are REAL, and letting this propagate would lose the record of
    them. A trial that ends this way is not a model failure and must not
    sit in the pass-rate denominator."""

    def __init__(self, detail, attempts):
        self.detail, self.attempts = detail, attempts
        super().__init__("%s (after %d attempts)" % (detail, attempts))


class LiveFatalError(Exception):
    """A call failed for a reason no amount of retrying will fix - a bad
    key, no credits, an unknown model id, a malformed request.

    Separate from LiveTransportError so the battery ABORTS immediately.
    Sixty exponential backoffs against a typo'd model id is a forty-minute
    failure where a thirty-second one was available."""



# =====================================================================
# SCRIPTED
# =====================================================================
# One entry per case you have scripted. The value is the list of moves
# the "model" makes, in order.
#
# ADD YOUR OWN CASES HERE. To script a case: work out what a correct
# agent would do, step by step, and write the steps down. If you cannot
# write them down, you do not yet understand the case - which is
# useful to discover now rather than at 2am on the 13th.
SCRIPTS = {

    # ---------------------------------------------------------------
    # PROBLEM B · REF-5602 - the booking from Appendix A.
    # Six tool calls. Turns 2 and 3 each fire two calls at once, so the
    # run is FOUR turns rather than six. See D2(c) in the brief.
    # ---------------------------------------------------------------
    "REF-5602": [
        {"thought": "I have a referral id and nothing else. Fetch the record.",
         "calls": [("get_referral", {"referral_id": "REF-5602"})]},

        {"thought": "Two things I need next do not depend on each other: "
                    "the specialty's rules, and whether this patient already "
                    "has an appointment. Fire both together.",
         "calls": [("check_referral_criteria", {"specialty": "OPH",
                                                "referral_id": "REF-5602"}),
                   ("lookup_patient", {"patient_id": "P-1180"})]},

        {"thought": "No red flag, right department, VF-01 attached, no "
                    "duplicate. Band is routine, so the window runs 8 weeks "
                    "from as_of 2026-09-09, to 2026-11-04. I will query both "
                    "halves of that window at once. This is a gamble: if the "
                    "near half had a slot, the second query was wasted.",
         "calls": [("get_clinic_slots", {"specialty": "OPH", "band": "routine",
                                         "from": "2026-09-09", "to": "2026-09-30"}),
                   ("get_clinic_slots", {"specialty": "OPH", "band": "routine",
                                         "from": "2026-10-01", "to": "2026-11-04"})]},

        {"thought": "OPH-C2 is full until 14 October. First bookable slot "
                    "inside the window is 2026-10-14 11:20. Book it - this is "
                    "the irreversible step, so it goes through the gate.",
         "calls": [("book_slot", {"clinic": "OPH-C2", "date": "2026-10-14",
                                  "time": "11:20", "referral_id": "REF-5602"})]},

        {"final": {
            "decision": "book",
            "booked": {"clinic": "OPH-C2", "date": "2026-10-14", "time": "11:20"},
            "reason": "Urgency band routine, so an 8-week window from as_of "
                      "2026-09-09 closing 2026-11-04; booked at 5 weeks. "
                      "VF-01 present. No existing OPH appointment for P-1180. "
                      "OPH-C2 was full until 2026-10-14.",
         },
         "thought": "Record the band, the window, the tests and the duplicate "
                    "check - the answer key asks for all four."},
    ],

    # ---------------------------------------------------------------
    # PROBLEM A · CLM-8842 - the partly payable claim from Appendix A.
    # Three lines, one of them excluded, one needing a pre-authorisation.
    # ---------------------------------------------------------------
    "CLM-8842": [
        {"thought": "Turn 1 must run alone: everything else needs the member, "
                    "the hospital and the LINE ITEMS this returns.",
         "calls": [("get_claim", {"claim_id": "CLM-8842"})]},

        # WHY THIS IS TWO TURNS AND APPENDIX A'S IS ONE.
        #
        # Appendix A folds lookup_policy and the three coverage checks
        # into a single turn and reaches this claim in four turns. We
        # cannot, and the reason is our own poka-yoke: check_coverage
        # takes a REQUIRED policy_id, and only lookup_policy can supply
        # one. A call and its own dependency cannot share a turn.
        #
        # This script used to do it anyway - it passed policy_id
        # "POL-3310" alongside the lookup_policy call that produces it,
        # which works only because a hand-written script already knows
        # the answer. No live model could reproduce that turn, so the
        # scripted baseline was measuring a shape the battery could
        # never match. Split, it costs one turn on every approval and
        # the number is honest. [brief D2(c): "a team that parallelises
        # less than we did and explained why is on stronger ground than
        # one that copied this page"]
        {"thought": "Two claim-level lookups that need nothing but the "
                    "record I already have. They do not need each other, "
                    "so they share a turn.",
         "calls": [("lookup_policy", {"member_id": "M-2214"}),
                   ("lookup_hospital", {"hospital_id": "H-114"})]},

        {"thought": "Now the policy id exists, so I can price the lines. "
                    "One coverage check PER LINE - three lines, three "
                    "checks, independent of each other, so one turn.",
         "calls": [("check_coverage", {"code": "47120", "policy_id": "POL-3310"}),
                   ("check_coverage", {"code": "31255", "policy_id": "POL-3310"}),
                   ("check_coverage", {"code": "62480", "policy_id": "POL-3310"})]},

        {"thought": "This one CANNOT join the turn above: I did not know which "
                    "line needed a pre-authorisation until coverage answered. "
                    "That is the dependency rule. Only 62480 needs one.",
         "calls": [("get_preauthorisation", {"member_id": "M-2214",
                                             "procedure_code": "62480",
                                             "date_of_service": "2026-09-02"})]},

        {"thought": "A disposition for every line, then send. This is the "
                    "irreversible step, so it goes through the gate - and it "
                    "is a turn like any other.",
         "calls": [("issue_decision_letter", {
             "claim_id": "CLM-8842",
             "decision": "approve_in_principle",
             "lines_resolved": 3,
             "approved_total": 2180,
             "refused_total": 300})]},

        {"final": {
            "decision": "approve_in_principle",
            "reason": "3 lines. 47120 covered (1400). 62480 covered, PA-5521 "
                      "cited, valid on 2026-09-02 (780). 31255 refused under "
                      "EX-14 cosmetic dermatology (300). approved_total 2180, "
                      "refused_total 300. H-114 is on panel.",
         },
         "thought": "Eight calls, four turns. Not an approve and not a "
                    "decline: one decision letter covering both."},
    ],
}


class ScriptedBackend:
    """Replays SCRIPTS[case_id]. Deterministic, free, offline."""

    name = "scripted"

    def __init__(self, case_id):
        if case_id not in SCRIPTS:
            raise SystemExit(
                "\n  No script for case %r.\n"
                "  The scripted backend replays moves you wrote down; it does\n"
                "  not invent them. Two ways forward:\n"
                "    1. add %r to SCRIPTS in backends.py, or\n"
                "    2. set BACKEND = \"live\" in config.py (this costs money).\n"
                "  Scripted cases so far: %s\n"
                % (case_id, case_id, ", ".join(sorted(SCRIPTS))))
        self.steps = SCRIPTS[case_id]
        self.i = 0

    def next_move(self, transcript):
        """`transcript` is ignored on purpose - a script does not react.
        That is what makes it reproducible."""
        if self.i >= len(self.steps):
            return {"final": {"decision": "escalate",
                              "reason": "script ended without a conclusion"},
                    "thought": "script exhausted"}
        step = self.steps[self.i]
        self.i += 1
        return step

    # Token counts on the scripted backend are ESTIMATES, so your cost
    # arithmetic has something to chew on. They are not measurements and
    # you must not report them as such - D6 wants MEASURED counts, which
    # means the live battery.
    @staticmethod
    def token_estimate(transcript):
        return 1800 + 600 * len(transcript), 120


# =====================================================================
# LIVE
# =====================================================================
class LiveBackend:
    """Real model through OpenRouter. Costs money. D5(b) only."""

    name = "live"

    def __init__(self, case_id, tool_descriptors, system_prompt):
        self.case_id = case_id
        self.tools = tool_descriptors
        self.system_prompt = system_prompt
        # The usage block from the most recent call. MEASURED, not
        # estimated - these come off the API response, which is what D6
        # requires and what makes the cost model checkable.
        self.last_tokens_in = 0
        self.last_tokens_out = 0
        self.usage_seen = False
        self.last_usage = {}
        self.last_meta = {}
        self.turn_usage = []      # the whole block, per turn

    def next_move(self, transcript):
        # >>> THE MODEL MUST BE TOLD WHICH CLAIM IT IS DECIDING <<<
        #
        # Until 2026-09-13 this list held ONLY the system prompt on turn 1:
        # 8,601 characters of rules and tool descriptors, and no claim id
        # anywhere. self.case_id was stored in __init__ and never sent. Every
        # live trial on every model asked for a decision on a claim it had not
        # been given - no model can pass that, however strong.
        #
        # NOTHING CAUGHT IT. ScriptedBackend replays moves with the id already
        # written in; the fake vendor in test_battery_fake.py is handed the case
        # directly by the test. Only a real model has to be told.
        #
        # Sent here rather than seeded into `transcript` on purpose: the
        # scripted token estimate is `1800 + 600 * len(transcript)`, so seeding
        # it would move every scripted, D2(c) and D7 number already in the
        # docs, for a fix that only the live path needs. JSON, not prose, so
        # every message after the system prompt keeps one format.
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps(
                {"task": "Decide the first response to this claim.",
                 "claim_id": self.case_id})},
        ]
        for entry in transcript:
            messages.append({"role": entry["role"], "content": entry["content"]})
        raw, usage, meta = LIVE_CALL(messages)
        # A CUT COMPLETION IS NOT A BAD ANSWER, and must not be graded as
        # one. Raise MAX_TOKENS_PER_CALL or shorten the contract; either
        # way the record has to name the real cause.
        if (meta or {}).get("finish_reason") == "length":
            self.last_tokens_in = int(usage.get("prompt_tokens") or 0)
            self.last_tokens_out = int(usage.get("completion_tokens") or 0)
            self.usage_seen = bool(usage)
            self.last_usage, self.last_meta = usage, meta
            self.turn_usage.append({"usage": usage, "meta": meta})
            return {"final": {"decision": "escalate",
                              "reason": "output truncated at max_tokens (%d) "
                                        "- the reply was cut mid-JSON"
                                        % config.MAX_TOKENS_PER_CALL,
                              "stopped_by": "output_truncated"},
                    "thought": "truncated: %s" % (raw or "")[:200]}
        # OpenRouter normalises to the OpenAI shape. If a provider omits
        # the block we record zero AND remember that we did, so a silent
        # zero is never mistaken for a cheap run.
        self.last_tokens_in = int(usage.get("prompt_tokens") or 0)
        self.last_tokens_out = int(usage.get("completion_tokens") or 0)
        self.usage_seen = bool(usage)
        self.last_usage, self.last_meta = usage, meta
        self.turn_usage.append({"usage": usage, "meta": meta})
        return _parse_move(raw)

    def token_estimate(self, transcript):
        """The counts the API billed for the turn just taken.

        `transcript` is accepted and ignored so the signature matches
        ScriptedBackend's - loop_agent calls this once per turn, straight
        after next_move, and must not care which backend it holds.
        """
        return self.last_tokens_in, self.last_tokens_out


def _parse_move(text):
    """The model must answer in JSON. Anything else is a run you cannot
    grade, so say so loudly rather than guessing.

    TOLERANT ABOUT THE WRAPPER, STRICT ABOUT THE CONTENT. Small
    instruction-tuned models fence their JSON or introduce it with a
    sentence. That is a formatting habit, not a wrong answer, and
    refusing it throws away a run that was otherwise correct.

    THIS WAS NOT A THEORY. rohit_panda's first live battery on
    meta-llama/llama-3.1-8b-instruct scored 0/60, and 38 of those 60
    trials died here - `turns: 0`, `evidence: []`, 165 output tokens
    produced and discarded. The model was answering; a bare json.loads
    was rejecting it. The three steps below are the same extraction
    evals/graders/judge.py already needed for the same reason.

    WHAT IT STILL REFUSES. Anything with no JSON object in it at all.
    The fallback stays loud and now keeps the raw text, because the old
    one discarded the evidence needed to diagnose exactly this.
    """
    raw = (text or "").strip()
    moves = []
    for candidate in _json_candidates(raw):
        try:
            move = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(move, dict) and ("final" in move or "calls" in move
                                       or "tool" in move):
            if candidate is raw:
                return move           # the whole reply is one clean move
            moves.append(move)

    # WHEN A REPLY HOLDS SEVERAL MOVES, THE LAST ONE IS THE ANSWER.
    #
    # A model that can see its own JSON history tends to echo it before
    # replying, so the earlier objects are what it already did and the
    # last is what it means to do now. Taking the FIRST would re-execute
    # an echoed call - and the de-duplication guard would halt the run,
    # recreating the exact failure the transcript fix removed.
    #
    # This is a judgement, made before the raw text of a real failure was
    # available: until 2026-09-13 unparsed replies never reached the
    # results file. They do now (record["unparsed_raw"]), so the next live
    # run shows which pattern actually occurs. If the last object is ever
    # an echo, check_duplicate still catches it loudly.
    if moves:
        return moves[-1]
    return {"final": {"decision": "escalate",
                      "reason": "model did not return parseable JSON"},
            "thought": "unparseable: %s" % raw[:200],
            "unparsed_raw": raw[:2000]}


_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.S)


def _json_candidates(raw):
    """The substrings worth trying, cheapest and most likely first."""
    if not raw:
        return
    yield raw                                     # 1 · already clean JSON
    for m in _FENCE_RE.finditer(raw):             # 2 · ```json ... ```
        yield m.group(1)

    # 3 · EVERY COMPLETE OBJECT, in the order it appears.
    #
    # This used to be `raw[raw.find("{") : raw.rfind("}") + 1]` - the span
    # from the first brace to the last. It is right for ONE object wrapped
    # in prose and wrong the moment a reply holds two: the span swallows
    # the gap between them and nothing parses.
    #
    # That is exactly what the 2026-09-13 gate run hit. With the transcript
    # fixed, llama-3.1-8b could see its own previous move as JSON, and it
    # began echoing that move before writing its next one. 7 of 7 trials
    # were then filed as unparseable - including replies that contained a
    # perfectly valid move.
    #
    # raw_decode reads ONE complete object from a position and reports
    # where it ended, so a second object, trailing prose or an echoed move
    # cannot contaminate the first. _parse_move takes the first candidate
    # that is actually a move.
    decoder = json.JSONDecoder()
    pos = raw.find("{")
    while pos != -1:
        try:
            _obj, end = decoder.raw_decode(raw, pos)
        except ValueError:
            pos = raw.find("{", pos + 1)
            continue
        yield raw[pos:end]
        pos = raw.find("{", end)


_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
_FATAL_STATUS = {400: "malformed request", 401: "bad or missing API key",
                 402: "insufficient credits on this key",
                 403: "forbidden - key lacks access to this model",
                 404: "unknown model id"}


def _live_call(messages):
    """>>> THE ONLY FUNCTION IN THIS REPOSITORY THAT KNOWS A VENDOR <<<

    Everything else speaks in terms of moves and transcripts. Swapping
    vendor means rewriting this one function, and changing MODEL and
    BASE_URL in config.py. Nothing else.

    Returns (content, usage, meta). `usage` is the MEASURED token count -
    discarding it and estimating instead is the mistake D6 punishes, and
    it is why every live run here used to report a cost of exactly zero.
    `meta` carries which model and provider ACTUALLY served the call:
    OpenRouter routes across providers, so two members requesting the
    same slug can be served different quantisations, and the only way to
    notice is to record it.

    RETRY LIVES HERE, NOT AROUND THE TRIAL. Retrying a whole trial after
    a failure at turn 6 re-sends and re-pays for turns 1 to 5. Retrying
    the HTTP call preserves the transcript and the spend.
    """
    key = config.api_key()
    if not key:
        raise LiveFatalError(
            "\n  BACKEND is 'live' but no API key is set.\n"
            "    export OPENROUTER_API_KEY='sk-or-...'\n"
            "  or call config.set_api_key(...) before running.\n"
            "  Or set BACKEND = 'scripted' in config.py, which is free.\n")

    body = {
        "model": config.MODEL,
        "messages": messages,
        "temperature": config.TEMPERATURE,
        # A SPEND CONTROL, not a quality setting. MAX_TOKENS_PER_RUN in
        # guardrails.py fires only AFTER the tokens are billed; this is
        # the one thing that stops a runaway completion being paid for.
        "max_tokens": config.MAX_TOKENS_PER_CALL,
        # Ask the vendor for its own cost figure so ours can be checked
        # against it rather than merely asserted.
        "usage": {"include": True},
    }
    if not getattr(config, "ALLOW_REASONING", False):
        # Hidden thinking bills as OUTPUT, at 4-5x input. `exclude` would
        # only hide it while still charging - so turn it off, not away.
        body["reasoning"] = {"enabled": False}

    data = json.dumps(body).encode()
    last = ""
    for attempt in range(1, config.RETRY_MAX + 1):
        req = urllib.request.Request(
            config.BASE_URL.rstrip("/") + "/chat/completions",
            data=data,
            headers={"Authorization": "Bearer " + key,
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as r:
                payload = json.load(r)
            break
        except urllib.error.HTTPError as err:
            if err.code in _FATAL_STATUS:
                raise LiveFatalError("HTTP %d - %s" % (err.code,
                                                       _FATAL_STATUS[err.code]))
            if err.code not in _RETRYABLE_STATUS:
                raise LiveFatalError("HTTP %d - unexpected" % err.code)
            last = "HTTP %d" % err.code
            _sleep_before_retry(attempt, err.headers.get("Retry-After"))
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            last = "%s: %s" % (type(err).__name__, err)
            _sleep_before_retry(attempt, None)
    else:
        raise LiveTransportError(last, config.RETRY_MAX)

    choice = (payload.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    return (content,
            payload.get("usage") or {},
            {"served_model": payload.get("model"),
             "provider": payload.get("provider"),
             "response_id": payload.get("id"),
             # WHY THE COMPLETION ENDED. "length" means the reply was cut
             # at max_tokens, so its JSON is severed mid-object and will
             # never parse. Without this the loop cannot tell a truncated
             # answer from a model that wrote prose, and reports both as
             # "did not return parseable JSON" - two different faults
             # needing two different fixes, filed under one name.
             "finish_reason": choice.get("finish_reason") or
                              choice.get("native_finish_reason")})


def _sleep_before_retry(attempt, retry_after):
    """Honour Retry-After when the vendor sends one; otherwise back off
    exponentially with jitter so six members retrying at once do not
    synchronise into a thundering herd against the same endpoint."""
    if retry_after:
        try:
            time.sleep(min(float(retry_after), 60.0))
            return
        except (TypeError, ValueError):
            pass
    time.sleep(min(config.RETRY_BASE_SECONDS * (2 ** (attempt - 1)), 30.0)
               + random.uniform(0, 1.0))


# THE TEST SEAM. evals/test_battery_fake.py rebinds this to a fake so the
# entire battery path - retry, resume, budget, provenance - is exercised
# without a key and without a dollar. One line, and it is the difference
# between a design nobody can test and one anybody can.
LIVE_CALL = _live_call


def make_backend(case_id, tool_descriptors=None, system_prompt=""):
    if config.BACKEND == "scripted":
        # A HAND-WRITTEN SCRIPT WINS. SCRIPTS holds the cases we reasoned
        # through by hand - the brief's worked example, and any case we
        # want to pin move-by-move. Everything else is derived by the
        # planner, so the whole 50-case set runs offline and free.
        if case_id in SCRIPTS:
            return ScriptedBackend(case_id)
        from .planner import PlannerBackend
        return PlannerBackend(case_id)
    if config.BACKEND == "live":
        return LiveBackend(case_id, tool_descriptors or [], system_prompt)
    raise SystemExit("BACKEND must be 'scripted' or 'live', not %r"
                     % config.BACKEND)
