"""
PE6201 · A2 scaffold — THE TOOL LAYER  (D2)
====================================================================
A tool reads ONE thing from the reference data and returns ONE fact.

THE NAMES BELOW ARE OURS, NOT YOURS. Appendix A says so and so does the
brief: these describe work that has to happen, not an interface you must
implement. Rename, re-argument, merge, split, add. What you cannot do is
change the ROUTING RULE or the GATED ACTION - the answer key is written
against those.

--------------------------------------------------------------------
HOW TO READ THIS FILE

Every tool carries the same comment block, and it is worth copying the
shape for your own tools:

    WHAT IT DOES   one sentence, in domain language
    READS          which JSON file(s) it touches
    RETURNS        the exact shape that comes back
    RETURNS NONE   when, AND WHAT THAT MEANS - these are different
    WATCH OUT      the mistake this tool exists to prevent

The fourth line is the one that separates a tool from a lookup. "Returns
None" is a fact about Python. "Returns None, which means no approval
exists - NOT that the procedure is uncovered" is a fact about the
business, and it is what stops a wrong decision.

--------------------------------------------------------------------
THE SIX-FIELD DESCRIPTOR (D2b)

EVERY tool below has one, at the bottom of this file. THEY ARE NOT
DECORATION - `prompt.build_system_prompt()` assembles them into the text
the model is actually sent, so editing one changes what the agent sees.

    python3 run_eval.py --prompt      shows the exact text, and its size

That is what makes D2(b) measurable. Rewrite the descriptors, print the
prompt, and the diff is precisely what you are claiming to have
measured. The v1 you compare against should be a genuinely worse version
you wrote - and note the prompt is resent EVERY TURN, so a longer
descriptor has to earn its length on every turn of every run.

--------------------------------------------------------------------
POKA-YOKE: make the wrong call impossible rather than documented.
Two examples below - `get_clinic_slots` demands a band so you cannot
accidentally book an urgent patient into a routine slot, and
`check_coverage` demands a policy_id so you cannot check coverage
against no policy at all.
====================================================================
"""
import datetime
import json
import os
from typing import Any, Dict, List, Literal, Optional, Union

import config


Decision = Literal["approve_in_principle", "request_document", "escalate"]

# This is both a static contract for callers and a runtime allow-list for
# untrusted model output. Literal alone is not runtime validation in Python.
_ALLOWED_DECISIONS = {
    "approve_in_principle", "request_document", "escalate"
}

_CACHE = {}

# ─────────────────────────────────────────────────────────────────────
# THE GATED-ACTION LEDGER  (D1, D3a)
# ─────────────────────────────────────────────────────────────────────
# Anchored to the repository root, NOT to the working directory. A
# relative path here would append to a different file depending on where
# you launched python from, which is how six team members end up with six
# partial ledgers and no way to tell which is which.
#   src/tools/tools.py -> src/tools -> src -> <repo root>
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DECISION_LOG_PATH = os.path.join(_REPO_ROOT, "logs", "decisions.jsonl")

# Claims decided during THE CURRENT RUN. Reset by reset_decision_state(),
# which loop_agent.run_case() calls before every run.
#
# WHY RESET, AND NOT A PERSISTENT LEDGER LOOKUP. D4 gives every negative
# case THREE trials, so the same claim_id is legitimately decided three
# times inside one process. A guard that remembered across runs would
# block trials 2 and 3 and report a duplicate that never happened - it
# would manufacture a 33% pass rate on every negative case. Isolation
# (GUARDRAILS 5.11: "no case may depend on a previous one having run")
# is the reason this set is per-run rather than per-process.
_DECIDED_THIS_RUN = set()

# WHAT THE LOOP KNOWS AND THE TOOL DOES NOT.
#
# Rubric 1, Technical Execution: "the gated action logs a decision with
# its evidence trail and its gate." The tool cannot see either. It is
# handed five totals; it has no idea which tools were called before it,
# how many turns that took, what the run has cost, or whether a human
# approved anything. Only the loop has those.
#
# So the loop deposits them here immediately before the gated call, and
# the ledger row is still written in ONE place - inside the gated action
# itself. That matters: a blocked call must leave no ledger line, and
# the only way to guarantee that is for the writer to be the thing doing
# the blocking. Writing the row from the loop instead would separate the
# refusal from the record and eventually they would disagree.
#
# Cleared per run, for the same isolation reason as _DECIDED_THIS_RUN.
_RUN_CONTEXT = {}


def reset_decision_state():
    """Clear per-run gated-action state. Called at the top of every run."""
    _DECIDED_THIS_RUN.clear()
    _RUN_CONTEXT.clear()


def set_run_context(**fields):
    """The loop's view of the run so far, for the ledger.

    Called by loop_agent just before the gated action. Never by a tool,
    never by the model, and nothing here can change what the gate
    DECIDES - it only changes what the ledger can SAY afterwards.
    """
    _RUN_CONTEXT.update(fields)


def _load(problem, table):
    """Read one JSON file, once, and keep it in memory.

    WHAT IT DOES   internal helper - the tools below read through it.
    WATCH OUT      the agent NEVER calls this and never sees these files.
                   It asks a tool a question and gets one answer back. An
                   agent handed all the data in its first prompt is making
                   a single call, not running a loop - which is exactly
                   what D0(a) asks you to defend.

    The cache is per-process, so a run never re-reads a file. It also
    means editing a JSON file mid-session has no effect until you
    restart - if the data looks stale, that is why.
    """
    key = (problem, table)
    if key not in _CACHE:
        path = os.path.join(config.data_root(), "data_%s" % problem,
                            "%s.json" % table)
        with open(path, encoding="utf-8") as fh:
            _CACHE[key] = json.load(fh)
    return _CACHE[key]


# =====================================================================
# PROBLEM B · outpatient referral coordination
# =====================================================================

def get_referral(referral_id):
    """Fetch the one referral the agent has been asked to handle.

    WHAT IT DOES   turns an id into the actual record: patient, specialty,
                   date, tests attached, and the GP's free-text summary.
    READS          data_B/referrals.json
    RETURNS        the referral row, or None
    RETURNS NONE   when no referral has that id. That is a BROKEN CASE,
                   not a business outcome - the agent was handed an id
                   that resolves to nothing. check_my_data.py exists to
                   catch this before a run ever happens.
    WATCH OUT      this is almost always turn 1 and it must run ALONE.
                   Everything else needs the patient_id and specialty it
                   returns, so nothing can be parallelised with it.

    Note what is NOT in the row it returns: no urgency, no red-flag
    verdict, no slot, no rule. Every one of those has to be fetched.
    That is what makes this an agent loop rather than one big call.
    """
    for r in _load("B", "referrals"):
        if r["referral_id"] == referral_id:
            return r
    return None


def lookup_patient(patient_id):
    """Who the patient is, what they already have booked, and how to
    reach them.

    WHAT IT DOES   answers the duplicate question and the contact question
                   in one call.
    READS          data_B/patients.json AND data_B/contacts.json
    RETURNS        {"patient": {...}, "contact": {...}}
    RETURNS NONE   when the patient_id matches nobody - again a broken
                   case, not an outcome.
    WATCH OUT      contacts and patients share the SAME KEY. Reading
                   contacts "through" patients would be a two-hop chain
                   and an extra turn for nothing. Both are fetched here
                   for that reason.

    THE DUPLICATE RULE, because this is where teams lose the case:
    `patient["existing_appointments"]` is a duplicate only when BOTH are
    true - the same specialty AND a date in the future, measured from
    as_of(). A past appointment in the same specialty is NOT a duplicate;
    the patient was seen and has been referred again. An empty list is
    normal and means nothing is booked.

    This tool does not decide that for you. It hands you the appointments
    and the decision is the agent's - which is deliberate, because the
    decision is what D4 grades.
    """
    p = next((x for x in _load("B", "patients")
              if x["patient_id"] == patient_id), None)
    if p is None:
        return None
    c = next((x for x in _load("B", "contacts")
              if x["patient_id"] == patient_id), None)
    return {"patient": p, "contact": c}


def check_referral_criteria(specialty, referral_id):
    """Run the department's protocol against this referral's free text.

    WHAT IT DOES   answers the four questions that can each end the run,
                   plus the urgency band, in one call.
    READS          data_B/specialties.json, data_B/urgency_bands.json,
                   and the referral itself
    RETURNS        {"red_flag_term":   the matched phrase, or None
                    "right_department": True/False
                    "missing_tests":   list of mandatory tests NOT attached
                    "band":            "urgent" | "soon" | "routine"
                    "window_weeks":    2 | 4 | 8}
    RETURNS NONE   when the referral or the specialty does not exist.
    WATCH OUT      THIS TOOL DECIDES NOTHING. It reports five facts. The
                   agent decides what they mean, and the ORDER matters:

                       red_flag_term is not None   -> ESCALATE, stop
                       right_department is False   -> ESCALATE, stop
                       missing_tests is non-empty  -> REQUEST INFO, stop
                       otherwise                   -> carry on to slots

                   An agent that queries a slot after finding a red flag
                   has failed the case even if it never books.

    WHY THIS IS ONE TOOL AND NOT FOUR - a design choice worth arguing
    with. The four questions are always asked, always in this order, and
    each can end the run. Splitting them into four tools would invite an
    agent to ask them out of order or skip one, and would cost three
    extra turns for no information. The cost is that this tool is doing
    four things, which is usually bad design.
    D2(a) marks your REASONING about the tool set, not ours - so if you
    split it, say why, and you are on perfectly good ground.

    HOW THE THREE TEXT CHECKS WORK, so you can see how crude they are:
      - red flags   substring match of the specialty's red_flag_terms
      - department  substring match of the specialty's `treats` words
      - band        first urgency band whose trigger_terms appear;
                    NO TRIGGER FOUND MEANS ROUTINE, which is the default
                    and not an error
    Substring matching is fragile on purpose. Your prompt-injection
    cases will attack exactly this, and improving it is fair game - just
    do not change the PROTOCOL, only how you detect it.
    """
    ref = get_referral(referral_id)
    spec = next((s for s in _load("B", "specialties")
                 if s["code"] == specialty), None)
    if ref is None or spec is None:
        return None
    text = ref["clinical_summary"].lower()

    red = next((t for t in spec["red_flag_terms"] if t.lower() in text), None)
    right_department = any(w.lower() in text for w in spec["treats"])
    attached = set(ref.get("tests_attached", []))
    missing = [t for t in spec["mandatory_tests"] if t["code"] not in attached]

    band, weeks = "routine", 8            # <- routine is the DEFAULT
    for b in _load("B", "urgency_bands"):
        if any(t.lower() in text for t in b["trigger_terms"]):
            band, weeks = b["band"], b["window_weeks"]
            break

    return {"red_flag_term": red,
            "right_department": right_department,
            "missing_tests": missing,
            "band": band,
            "window_weeks": weeks}


def get_clinic_slots(specialty, band, **window):
    """Find appointment slots that exist AND are free AND are legal.

    WHAT IT DOES   three filters at once: right department, right band,
                   inside the window, with a place left.
    READS          data_B/clinic_slots.json
    RETURNS        list of {clinic, specialty, band, date, time,
                   capacity_remaining} - possibly empty
    RETURNS EMPTY  when nothing is free in that window. EMPTY IS AN
                   ANSWER, not a failure: it means ESCALATE with trigger
                   `no_slot_in_window`. It does NOT mean widen the
                   window, and it does NOT mean drop to another band.
    WATCH OUT      capacity_remaining == 0 means the slot EXISTS AND IS
                   FULL. That is a different fact from the slot not
                   existing, and this tool filters those rows out for
                   you - so an empty list can mean either. If your
                   record needs to distinguish them, read the file.

    POKA-YOKE: `band` IS A REQUIRED ARGUMENT, and this is the clearest
    example in the scaffold of designing an interface so the wrong call
    cannot be made.

    On the shipped data, REF-5602 is a routine referral with an 8-week
    window closing 2026-11-04. THREE slots sit earlier inside that window
    with capacity free - OPH-C1 on 09-15 and 09-22 (urgent) and OPH-C3 on
    09-29 (soon). A team filtering by date alone books one of them and
    fails the case. Only the band excludes them, and making band an
    argument rather than an optional filter is what makes forgetting it
    impossible rather than merely documented.

    The window is passed as **kwargs so `from` can be used as a name -
    it is a Python keyword and cannot be a normal parameter. That is a
    small ugliness bought deliberately, to keep the domain word.
    """
    lo = window.get("from", "0000-00-00")
    hi = window.get("to", "9999-99-99")
    return [s for s in _load("B", "clinic_slots")
            if s["specialty"] == specialty
            and s["band"] == band
            and lo <= s["date"] <= hi
            and s["capacity_remaining"] > 0]


def book_slot(clinic, date, time, referral_id):
    """>>> THE IRREVERSIBLE STEP FOR PROBLEM B <<<

    WHAT IT DOES   commits the appointment. A patient is now expected at
                   a clinic on a date.
    READS          nothing - it WRITES, conceptually
    RETURNS        a confirmation carrying everything the record needs
    WATCH OUT      this is the ONE call in Problem B that cannot be taken
                   back. Every other tool can be re-run harmlessly.

    THIS IS WHAT THE AUTONOMY GATE SITS IN FRONT OF - see guardrails.py
    and the GATED_ACTION table below. Note WHERE the gate goes: in front
    of THIS ACTION, not in front of the agent as a whole. An agent gated
    as a whole is not an agent, it is a form, and D3(a) asks you to
    defend the placement.

    In this scaffold it returns a dict rather than touching anything -
    there is no real booking system. Your evaluation runs would be
    unrepeatable if there were, which is worth noticing: an agent that
    genuinely changes the world is much harder to test, and that is a
    real cost of autonomy, not a detail of this exercise.
    """
    return {"booked": True, "clinic": clinic, "date": date,
            "time": time, "referral_id": referral_id}


def as_of():
    """The clock for Problem B.

    WHAT IT DOES   returns the single date every urgency window is
                   measured FROM.
    READS          data_B/as_of.json
    RETURNS        a date string, e.g. "2026-09-09"
    WATCH OUT      windows are counted from THIS, not from the referral's
                   `date_received`. They happen to be equal for some
                   shipped referrals, which is exactly the sort of
                   coincidence that hides a bug until a case where they
                   differ.

    Move this date and every booking case in the answer key silently
    becomes wrong. The data guide says leave it alone, and it means it.
    """
    return _load("B", "as_of")["as_of"]


# =====================================================================
# PROBLEM A · health-insurance claim first response
# =====================================================================

def get_claim(claim_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the one claim the agent has been asked to decide.

    WHAT IT DOES   turns an id into the record: member, hospital, date,
                   attached documents, the member's narrative, and the
                   LINE ITEMS.
    READS          data_A/claims.json
    RETURNS        the claim row, or None
    RETURNS NONE   when no claim has that id - a broken case, not an
                   outcome.
    WATCH OUT      `lines` is a LIST. Nine of the fifteen shipped claims
                   have one line; six have two to four. Every line needs
                   its own coverage check and its own disposition, and an
                   agent that checks only the first line quietly approves
                   things it should refuse.

    Like get_referral, this must run ALONE on turn 1 - everything after
    it needs the member, the hospital and the lines it returns. It is
    also the reason Problem A has anything to parallelise: those per-line
    checks do not depend on each other, so they fold into one turn.
    """
    for c in _load("A", "claims"):
        if c["claim_id"] == claim_id:
            return c
    return None


def lookup_policy(member_id: str) -> Optional[Dict[str, Any]]:
    """Follow the claim to the money and the rules.

    WHAT IT DOES   claim -> member -> policy, and does the headroom
                   arithmetic for you.
    READS          data_A/members.json AND data_A/policies.json
    RETURNS        {"member": {...}, "policy": {...}, "remaining": int}
    RETURNS NONE   when the member or their policy does not exist.
    WATCH OUT      `remaining` is annual_limit MINUS used_to_date. The
                   claim total is tested against THAT, not against
                   annual_limit. Testing against the limit is a silent
                   wrong answer on any policy with spend on it.

    THREE SEPARATE REASONS TO REFUSE live in the row this returns, and
    they are easy to conflate:
      1. status == "lapsed"              -> escalate, nothing else matters
      2. date_of_service outside
         start_date .. end_date          -> escalate, even if status is active
      3. lines exceed `remaining`         -> escalate
    Note (2): a policy can say "active" and still not cover the date. The
    shipped data has a claim that tests exactly this.

    The member row itself carries NO decision information - it is a
    bridge. `join_date` in particular is not a coverage date; the
    policy's own dates govern.
    """
    m = next((x for x in _load("A", "members")
              if x["member_id"] == member_id), None)
    if m is None:
        return None
    p = next((x for x in _load("A", "policies")
              if x["policy_id"] == m["policy_id"]), None)
    if p is None:
        return None
    return {"member": m, "policy": p,
            "remaining": p["annual_limit"] - p["used_to_date"]}


def lookup_hospital(hospital_id: str) -> Optional[Dict[str, Any]]:
    """Is the hospital inside the insurer's network?

    WHAT IT DOES   one boolean and a name.
    READS          data_A/hospitals.json
    RETURNS        {hospital_id, name, panel, country} or None
    WATCH OUT      panel status does NOT by itself decide the claim. A
                   non-panel hospital means the member paid and is
                   claiming it back rather than the insurer settling
                   directly - so it changes what the record must SAY, not
                   what the decision IS.

    It is still a required call. An agent that never checked cannot
    claim it did, and the decision record is what a marker reads.
    """
    return next((h for h in _load("A", "hospitals")
                 if h["hospital_id"] == hospital_id), None)


def check_coverage(code: str, policy_id: str,
                   documents_attached: Optional[List[str]] = None
                   ) -> Optional[Dict[str, Any]]:
    """Is this ONE procedure payable under THIS policy?

    WHAT IT DOES   resolves one line item: what the code means, whether
                   it needed permission first, and whether this product
                   excludes it.
    READS          data_A/procedures.json AND data_A/policies.json
    RETURNS        {"code", "description", "requires_preauth" (bool),
                    "excluded" (bool), "exclusion_rule" (str or None)}
    RETURNS NONE   when the policy record does not exist. An unknown
                   procedure code or malformed argument is rejected at the
                   boundary, before the lookup.
    WATCH OUT      CALL THIS ONCE PER LINE. A three-line claim needs
                   three calls - and because they are independent of each
                   other, all three belong in the same turn.

    TWO FIELDS THAT DRIVE EVERYTHING AFTER THIS:

      `requires_preauth` is THE BRANCH. True means go and look for an
      approval; False means do not. This single boolean is why claims
      vary in run length, and an agent that calls get_preauthorisation
      for every line has not read it.

      `excluded` refuses THE LINE, not the claim. Three lines approved
      and one excluded is ONE decision letter covering both - "approve in
      principle" with a disposition per line. Escalating the whole claim
      because one line is excluded is a distinct, and common, failure.
      When excluded, `exclusion_rule` gives you the rule id to cite; the
      record should name it, not merely say "excluded".

    POKA-YOKE: `policy_id` is REQUIRED. Coverage is meaningless without a
    policy, and a tool that let you omit it would cheerfully return an
    answer about nothing at all.

    --------------------------------------------------------------------
    D2(a) - WHY THE DOCUMENT CHECK LIVES HERE AND NOT IN ITS OWN TOOL

    Appendix A's routing table has a row we could not reach: "a required
    document is absent -> request_document". Nothing read
    required_documents.json, so three cases in our set (CLM-8901,
    CLM-9029, CLM-9030) were unreachable by any correct trajectory.

    D2(a) says: before you add a tool, try not adding one. Four moves, in
    order of preference. We tried them in that order and stopped at move
    2, and this is what that looks like in code:

      1 widen an existing tool's parameters   -> done: `documents_attached`
      2 return more from one call             -> done: `required_document`
                                                 and `document_attached`
      3 move the step into ordinary code      -> rejected: the agent must
                                                 be able to NAME the
                                                 document in its request,
                                                 so it has to see it
      4 add the tool                          -> not needed

    A get_required_documents tool would have cost a definition in the
    prompt prefix - re-sent and re-billed on EVERY turn of EVERY run,
    called or not - plus one more call per line, plus a confusable
    neighbour: "when do I use check_coverage rather than
    get_required_documents?" is a question we could not answer in one
    line, which by D2(a) question 2 is the signal to merge them.

    The cost of the merge is ~15 tokens per observation and zero extra
    turns. That trade is the whole of lever 1 vs lever 3 in D6, and it is
    measurable: run `python3 run_eval.py --prompt` before and after.
    """
    _validate_procedure_code(code)
    _validate_text(policy_id, "policy_id")
    if documents_attached is not None:
        if not isinstance(documents_attached, list):
            raise TypeError("documents_attached must be a list of strings")
        if not all(isinstance(item, str) for item in documents_attached):
            raise TypeError("documents_attached must be a list of strings")

    proc = next((p for p in _load("A", "procedures") if p["code"] == code), None)
    pol = next((p for p in _load("A", "policies")
                if p["policy_id"] == policy_id), None)
    if proc is None or pol is None:
        return None
    excl = next((e for e in pol["exclusions"] if e["code"] == code), None)

    # Which document, if any, this procedure cannot be assessed without.
    required = next((r["document"] for r in _load("A", "required_documents")
                     if r["procedure_code"] == code), None)
    # None (not False) when no document is required: "no rule applies" and
    # "a rule applies and is unmet" are different facts and must not
    # collapse into one falsy value.
    attached = None
    if required is not None and documents_attached is not None:
        attached = required in documents_attached

    return {"code": code,
            "description": proc["description"],
            "requires_preauth": proc["requires_preauth"],
            "excluded": excl is not None,
            "exclusion_rule": excl["rule"] if excl else None,
            "required_document": required,
            "document_attached": attached}


def get_preauthorisation(member_id: str, procedure_code: str,
                         date_of_service: str
                         ) -> Optional[Dict[str, Any]]:
    """Was permission granted BEFORE treatment, and is it still good?

    WHAT IT DOES   looks for an approval matching this member AND this
                   procedure AND valid on this date.
    READS          data_A/preauthorisations.json
    RETURNS        {preauth_id, member_id, procedure_code, valid_from,
                    valid_to} or None
    RETURNS NONE   in TWO different situations that this tool cannot tell
                   apart: no approval was ever granted, OR one exists but
                   had expired before the date of service.
    WATCH OUT      >>> NONE DOES NOT MEAN "NOT COVERED". <<<

    This is the single most expensive misreading available in Problem A.
    None means THE EVIDENCE IS MISSING, which under the routing table is
    a REQUEST - "pre-authorisation reference for 62480, valid on
    2026-09-02" - naming the code and the date. It is not a refusal, and
    deciding otherwise fails the case.

    ALL THREE conditions must hold for a match. An approval for the right
    procedure belonging to another member does not count. An approval for
    the right member and procedure that expired the day before treatment
    does not count either - the shipped data has one of each, precisely
    so a partial match is punished.

    Call this ONLY when check_coverage said requires_preauth is True.
    """
    _validate_text(member_id, "member_id")
    _validate_procedure_code(procedure_code)
    _validate_iso_date(date_of_service, "date_of_service")

    for pa in _load("A", "preauthorisations"):
        if (pa["member_id"] == member_id
                and pa["procedure_code"] == procedure_code
                and pa["valid_from"] <= date_of_service <= pa["valid_to"]):
            return pa
    return None


def check_duplicate_claim(member_id: str, hospital_id: str,
                          date_of_service: str, lines: List[Dict[str, Any]]
                          ) -> Optional[Dict[str, Any]]:
    """Has this episode already been decided?

    WHAT IT DOES   compares the claim against the claims history on ALL
                   FOUR facts.
    READS          data_A/decided_claims.json
    RETURNS        the prior decision row, or None
    RETURNS NONE   when nothing matches - which is the normal case and
                   means carry on.
    WATCH OUT      THE CLAIM ID IS NOT ONE OF THE FACTS. A resubmission
                   arrives with a NEW id, so matching on it finds nothing,
                   ever, and the case fails silently.

    MATCH ON ALL FOUR: member, hospital, date of service, lines. The
    shipped history holds four rows and only ONE queued claim is a true
    duplicate of any of them. The other three history rows are
    NEAR-MISSES, each differing from a real claim on exactly one fact:

        CLM-8710  vs CLM-8933   nothing differs - the true duplicate
        CLM-8702  vs CLM-8850   the date of service differs
        CLM-8726  vs CLM-8960   the LINES differ
        CLM-8688  vs nothing    just history to walk past

    So an agent matching on the date alone, or on member and date, or on
    member and hospital and date, WRONGLY ESCALATES a claim that is
    perfectly fine. Only the full comparison gets all fifteen right. The
    near-misses are in the data deliberately, to make that testable.
    """
    def norm(ls):
        return sorted((l["code"], l["amount"]) for l in ls)
    for d in _load("A", "decided_claims"):
        if (d["member_id"] == member_id
                and d["hospital_id"] == hospital_id
                and d["date_of_service"] == date_of_service
                and norm(d["lines"]) == norm(lines)):
            return d
    return None


def issue_decision_letter(
        claim_id: str,
        decision: Decision,
        lines_resolved: int,
        approved_total: Union[int, float],
        refused_total: Union[int, float] = 0,
        ) -> Dict[str, Any]:
    """>>> THE IRREVERSIBLE STEP FOR PROBLEM A <<<

    WHAT IT DOES   sends the decision to the member. The insurer is now
                   committed to it.
    READS          nothing - it WRITES, conceptually
    RETURNS        a confirmation carrying the totals for the record
    WATCH OUT      everything before this can be re-run harmlessly. This
                   one cannot be taken back, which is what makes it the
                   gated action - see GATED_ACTION below.

    IT IS A TURN LIKE ANY OTHER. Gated, not free. Appendix A's CLM-8842
    record counts it as turn 4 of 4, and your D2(c) arithmetic has to
    count it too.

    `lines_resolved` is here on purpose: it forces the agent to state how
    many lines it actually disposed of, which makes "I only checked the
    first line" visible in the record instead of invisible.

    THREE THINGS THIS FUNCTION ENFORCES, rather than merely asserting:

      1. ONCE ONLY. A second decision on the same claim in the same run is
         BLOCKED, whatever arguments it carries. Action de-duplication in
         guardrails.py keys on (tool, args) and so would let a second call
         through if a single number differed; this does not.
      2. THE CLAIM EXISTS. A decision on a claim_id that resolves to
         nothing is refused rather than recorded.
      3. THE ARITHMETIC IS THE RECORD'S, NOT THE MODEL'S. For an approve,
         lines_resolved and the two totals are re-derived from the claim
         and compared. A model that checked one line of four cannot write
         lines_resolved: 4 and have it believed.

    Check 3 applies to approve_in_principle ONLY, and that is deliberate.
    Appendix A's escalate example stops at two turns with the lines never
    individually priced - "the claim cannot be decided at this level
    regardless of coverage" - and an early exit there is CORRECT behaviour,
    not a truncated run. Requiring a full line reconciliation on every
    outcome would fail the annual_limit_exceeded case by design.

    A blocked call returns {"sent": False, "error": ...} and writes
    NOTHING to the ledger. The block is loud: the agent reads the error as
    its observation and the reason appears in the run record.
    """
    # Literal annotations help type checkers, but Python does not enforce
    # them at runtime. This explicit check prevents a model's free string
    # from becoming an unrecognised decision in the ledger.
    if (not isinstance(decision, str)
            or decision not in _ALLOWED_DECISIONS):
        return {"sent": False,
                "error": "BLOCKED: invalid decision %r; expected one of %s"
                         % (decision, ", ".join(sorted(_ALLOWED_DECISIONS)))}
    if not isinstance(claim_id, str) or not claim_id.strip():
        return {"sent": False,
                "error": "BLOCKED: claim_id must be a non-empty string"}
    if (isinstance(lines_resolved, bool)
            or not isinstance(lines_resolved, int)
            or lines_resolved < 0):
        return {"sent": False,
                "error": "BLOCKED: lines_resolved must be a non-negative integer"}
    if not _is_non_negative_number(approved_total):
        return {"sent": False,
                "error": "BLOCKED: approved_total must be non-negative"}
    if not _is_non_negative_number(refused_total):
        return {"sent": False,
                "error": "BLOCKED: refused_total must be non-negative"}

    # 1 · ONCE ONLY, per run.
    if claim_id in _DECIDED_THIS_RUN:
        return {"sent": False,
                "error": "BLOCKED: duplicate - a decision already exists "
                         "for %s in this run" % claim_id}

    # 2 · The claim must exist.
    claim = get_claim(claim_id)
    if claim is None:
        return {"sent": False,
                "error": "BLOCKED: no claim %s exists - nothing to decide"
                         % claim_id}

    # 3 · Re-derive what the model asserted. Approvals only; see above.
    if decision == "approve_in_principle":
        lines = claim.get("lines", []) or []
        if lines_resolved != len(lines):
            return {"sent": False,
                    "error": "BLOCKED: lines_resolved is %r but claim %s has "
                             "%d lines - you have not finished"
                             % (lines_resolved, claim_id, len(lines))}
        expected_total = sum(l["amount"] for l in lines)
        if round(approved_total + refused_total, 2) != round(expected_total, 2):
            return {"sent": False,
                    "error": "BLOCKED: approved_total %r + refused_total %r "
                             "is %r, but the lines on %s total %r"
                             % (approved_total, refused_total,
                                round(approved_total + refused_total, 2),
                                claim_id, expected_total)}

    # ---- the write ---------------------------------------------------
    _DECIDED_THIS_RUN.add(claim_id)
    # THE LEDGER ROW. Not a letter, not a template, not prose - the
    # brief is explicit that no marks live in the wording. What earns
    # the mark is that the row is auditable on its own: months later,
    # somebody must be able to read one line and say what was decided,
    # on what evidence, through which gate, and what it cost.
    record = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "case_id": claim_id,
        "decision": decision,
        "lines_resolved": lines_resolved,
        "approved_total": approved_total,
        "refused_total": refused_total,
        "autonomy": config.AUTONOMY,
        # WHY, in the agent's own words at the moment it committed - not
        # the tidied-up reason it writes afterwards. If the two ever
        # disagree, this is the one that tells you what it believed.
        "reason": _RUN_CONTEXT.get("thought_at_issue"),
        # THE EVIDENCE TRAIL: every tool actually called, in order,
        # before this write. A decision whose trail does not contain
        # check_coverage is a decision nobody checked coverage for, and
        # that is readable straight off the row.
        "evidence": list(_RUN_CONTEXT.get("evidence") or []),
        # THE GATE: which one, and whether a human passed it.
        "gate": _RUN_CONTEXT.get("gate"),
        "turns": _RUN_CONTEXT.get("turns"),
        "tokens_in": _RUN_CONTEXT.get("tokens_in"),
        "tokens_out": _RUN_CONTEXT.get("tokens_out"),
        "cost_usd": _RUN_CONTEXT.get("cost_usd"),
        "backend": _RUN_CONTEXT.get("backend", config.BACKEND),
    }
    os.makedirs(os.path.dirname(DECISION_LOG_PATH), exist_ok=True)
    with open(DECISION_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    # The RETURN SHAPE IS UNCHANGED on the success path, because the
    # descriptor promises it and backends.py scripts read it.
    return {"sent": True, "claim_id": claim_id, "decision": decision,
            "lines_resolved": lines_resolved,
            "approved_total": approved_total, "refused_total": refused_total}


# =====================================================================
# THE REGISTRY
# =====================================================================
# What the agent is allowed to call, per problem. Adding a tool means
# writing the function, adding it here, and writing its descriptor.
REGISTRY = {
    "B": {
        "get_referral": get_referral,
        "lookup_patient": lookup_patient,
        "check_referral_criteria": check_referral_criteria,
        "get_clinic_slots": get_clinic_slots,
        "book_slot": book_slot,
        "as_of": as_of,
    },
    "A": {
        "get_claim": get_claim,
        "lookup_policy": lookup_policy,
        "lookup_hospital": lookup_hospital,
        "check_coverage": check_coverage,
        "get_preauthorisation": get_preauthorisation,
        "check_duplicate_claim": check_duplicate_claim,
        "issue_decision_letter": issue_decision_letter,
    },
}

# THE ONE IRREVERSIBLE ACTION PER PROBLEM. Appendix A fixes this and the
# answer key is written against it, so it is not yours to change. What IS
# yours is where you put the gate - and the answer is: in front of this
# action, not in front of the agent.
GATED_ACTION = {"B": "book_slot", "A": "issue_decision_letter"}


# =====================================================================
# THE SIX-FIELD DESCRIPTORS  (D2b)
# =====================================================================
# Two worked examples. Write one for EVERY tool you ship, and note that
# the descriptor is what the MODEL reads - the comments above are what
# YOU read. They overlap, but they are not the same document: a
# descriptor is written to be acted on, a comment to be understood.
DESCRIPTORS = {
    # ---- Problem B -------------------------------------------------
    "get_referral": {
        "name": "get_referral",
        "purpose": "Fetch the referral you have been asked to handle.",
        "when": "Turn 1, alone. Everything else needs what it returns, so "
                "nothing can be run alongside it.",
        "args": {"referral_id": "str, the case id you were given"},
        "returns": "{referral_id, patient_id, referring_clinic, specialty, "
                   "date_received, clinical_summary, tests_attached, "
                   "tests_attached_on (may be absent)}",
        "failure": "Returns None when no referral has that id. That is a "
                   "broken case, not an outcome - stop and say so rather "
                   "than inventing a decision.",
    },
    "lookup_patient": {
        "name": "lookup_patient",
        "purpose": "The patient's existing appointments and how to contact them.",
        "when": "Any time after get_referral. Independent of the criteria "
                "check, so the two can go in one turn.",
        "args": {"patient_id": "str, from the referral"},
        "returns": "{patient: {patient_id, date_of_birth, "
                   "existing_appointments[]}, contact: {method, value}}",
        "failure": "Returns None when the patient does not exist - a broken "
                   "case. An EMPTY existing_appointments list is normal and "
                   "means nothing is booked, which is not the same thing.",
    },
    "check_referral_criteria": {
        "name": "check_referral_criteria",
        "purpose": "Run the department's protocol against the referral's free "
                   "text: red flags, right department, mandatory tests, band.",
        "when": "Immediately after get_referral. Its answers decide whether "
                "the run continues at all.",
        "args": {"specialty": "str, the code on the referral",
                 "referral_id": "str, the case id"},
        "returns": "{red_flag_term (str or None), right_department (bool), "
                   "missing_tests (list), band, window_weeks}",
        "failure": "Returns None when the referral or specialty does not "
                   "exist. IT DECIDES NOTHING - it reports five facts. Apply "
                   "them in order: red flag, then wrong department, then "
                   "missing test, then duplicate. STOP at the first that "
                   "fires. band 'routine' is the default when no trigger "
                   "phrase appears; that is normal, not a failure.",
    },
    "book_slot": {
        "name": "book_slot",
        "purpose": "Commit the appointment. THE IRREVERSIBLE STEP.",
        "when": "Last, and only when all four checks passed and a legal slot "
                "was found. Never speculatively.",
        "args": {"clinic": "str, from the chosen slot",
                 "date": "str, from the chosen slot",
                 "time": "str, from the chosen slot",
                 "referral_id": "str, the case id"},
        "returns": "{booked: true, clinic, date, time, referral_id}",
        "failure": "This call is GATED: it may be held for human approval "
                   "depending on the autonomy setting. If it is held, that is "
                   "the correct outcome and not an error - report that the "
                   "booking awaits approval, and name the slot you would take.",
        "irreversible": "YES. This is the one irreversible step in Problem B - "
                        "it consumes a scarce slot and tells a patient a date. "
                        "The gate in front of it is the autonomy setting in "
                        "config.py.",
    },
    "as_of": {
        "name": "as_of",
        "purpose": "The date every urgency window is measured FROM.",
        "when": "Before computing any window. Cheap - call it rather than "
                "assuming.",
        "args": {},
        "returns": "a date string, e.g. '2026-09-09'",
        "failure": "Never fails. WATCH OUT: windows are counted from THIS, "
                   "not from the referral's date_received. They are equal on "
                   "some referrals and not on others.",
    },

    # ---- Problem A -------------------------------------------------
    "get_claim": {
        "name": "get_claim",
        "signature": "get_claim(claim_id: str) -> ClaimRecord",
        "what": "Resolve the supplied claim id to the claim record needed for the first response.",
        "purpose": "Fetch the claim you have been asked to decide.",
        "when": "Turn 1, alone. Everything else needs the member, hospital "
                "and line items it returns.",
        "args": {"claim_id": "str, the case id you were given"},
        "returns": "{claim_id, member_id, hospital_id, date_of_service, "
                   "narrative, documents[], lines[{code, amount}]}",
        "failure": "Returns None when no claim has that id - a broken case. "
                   "NOTE lines is a LIST: every line needs its own coverage "
                   "check and its own disposition.",
        "irreversible": "NO. This is a read-only lookup.",
    },
    "lookup_policy": {
        "name": "lookup_policy",
        "signature": "lookup_policy(member_id: str) -> PolicyContext",
        "what": "Resolve the member's policy and remaining annual headroom.",
        "purpose": "The member's policy, and how much of the annual limit is "
                   "left.",
        "when": "After get_claim. Independent of the coverage checks and the "
                "hospital lookup, so all of them fit in one turn.",
        "args": {"member_id": "str, from the claim"},
        "returns": "{member: {...}, policy: {status, start_date, end_date, "
                   "annual_limit, used_to_date, exclusions[]}, remaining: int}",
        "failure": "Returns None when the member or policy does not exist. "
                   "USE `remaining`, not annual_limit - it is the limit minus "
                   "what is already spent. Three separate escalation reasons "
                   "live here: lapsed status, a date of service outside "
                   "start_date..end_date EVEN IF status is active, and lines "
                   "exceeding `remaining`.",
        "irreversible": "NO. This is a read-only lookup.",
    },
    "lookup_hospital": {
        "name": "lookup_hospital",
        "signature": "lookup_hospital(hospital_id: str) -> HospitalRecord | None",
        "what": "Resolve whether the hospital is on the insurer's panel.",
        "purpose": "Whether the hospital is on the insurer's panel.",
        "when": "After get_claim, alongside the other independent lookups.",
        "args": {"hospital_id": "str, from the claim"},
        "returns": "{hospital_id, name, panel (bool), country}",
        "failure": "Returns None when the hospital does not exist. panel "
                   "false does NOT decide the claim - it changes what the "
                   "record must SAY, not what the decision is. Record it "
                   "either way.",
        "irreversible": "NO. This is a read-only lookup.",
    },
    "check_coverage": {
        "name": "check_coverage",
        "signature": "check_coverage(code: str, policy_id: str, documents_attached: list[str] | None = None) -> CoverageResult | None",
        "what": "Resolve coverage, exclusion, pre-authorisation and required-document facts for one procedure line.",
        "purpose": "Whether ONE procedure code is payable under ONE policy.",
        "when": "ONCE PER LINE. A three-line claim needs three calls, and "
                "they are independent, so they belong in the same turn.",
        "args": {"code": "str, a known procedure code from procedures.json; an unknown code is rejected at the boundary",
                 "policy_id": "str, REQUIRED, from lookup_policy; an empty or non-string value is rejected",
                 "documents_attached": "list[str] | None, the claim's documents[] list; malformed lists are rejected; used to test required-document presence"},
        "returns": "{code, description, requires_preauth (bool), excluded (bool), exclusion_rule (str|None), required_document (str|None), document_attached (bool|None)}; exactly one line, <= 7 fields, <= 60 tokens; never a list.",
        "failure": "Returns None when the policy record is absent. Rejects a non-string/unknown procedure code or malformed arguments before lookup. "
                   "THREE FIELDS DRIVE WHAT HAPPENS NEXT: requires_preauth "
                   "true means look for an approval, false means do not. "
                   "excluded refuses THAT LINE, not the claim - cite "
                   "exclusion_rule by name and keep deciding the other lines. "
                   "document_attached false means REQUEST that document, "
                   "naming it and the line; document_attached null means no "
                   "document rule applies to this code, which is not the same "
                   "thing and is not a problem.",
        "irreversible": "NO. This is a read-only lookup.",
    },
    "check_duplicate_claim": {
        "name": "check_duplicate_claim",
        "signature": "check_duplicate_claim(member_id: str, hospital_id: str, date_of_service: str, lines: list[dict]) -> PriorDecision | None",
        "what": "Compare the episode against decided-claim history using all four business facts.",
        "purpose": "Whether this episode has already been decided.",
        "when": "Before issuing any decision.",
        "args": {"member_id": "str, from the claim",
                 "hospital_id": "str, from the claim",
                 "date_of_service": "str, from the claim",
                 "lines": "the claim's lines list, unchanged"},
        "returns": "one prior decided-claim record <= 8 fields and <= 80 tokens, or None",
        "failure": "Returns None when nothing matches - the normal case, "
                   "carry on. MATCH ON ALL FOUR FACTS. The claim id is NOT "
                   "one of them: a resubmission arrives with a new id. The "
                   "history contains near-misses that differ on exactly one "
                   "fact each, so any shortcut match wrongly escalates a "
                   "perfectly good claim.",
        "irreversible": "NO. This is a read-only lookup.",
    },
    "issue_decision_letter": {
        "name": "issue_decision_letter",
        "signature": "issue_decision_letter(claim_id: str, decision: Literal['approve_in_principle','request_document','escalate'], lines_resolved: int, approved_total: int|float, refused_total: int|float = 0) -> DecisionWriteResult",
        "what": "Send an APPROVE_IN_PRINCIPLE, and nothing else: append exactly one simulated first-response decision record after the loop's autonomy gate. A request_document or an escalate is never sent - finish with final instead. The signature lists all three outcomes so a fourth cannot be invented; that does not make all three sendable.",
        "purpose": "Send the decision to the member. THE IRREVERSIBLE STEP.",
        "when": "ONLY to send an approve_in_principle, as the last call. A request_document or an escalate is never sent - finish with final instead. The signature lists all three outcomes so that a fourth cannot be invented; it does not mean all three are sent.",
        "args": {"claim_id": "str, the case id; unknown ids are refused",
                 "decision": "Literal['approve_in_principle','request_document','escalate']; any other value is refused",
                 "lines_resolved": "int >= 0, how many lines you actually decided",
                 "approved_total": "int|float >= 0, dollars approved",
                 "refused_total": "int|float >= 0, dollars refused (default 0)"},
        "returns": "on success {sent: true, claim_id, decision, "
                   "lines_resolved, approved_total, refused_total} - at most "
                   "6 fields, ~40 tokens. On a refused call {sent: false, "
                   "error} - one line naming what was wrong.",
        "failure": "This call is GATED by the loop and may be held for human approval. "
                   "If held, that is the correct outcome, not an error. It is "
                   "also REFUSED, with sent:false, in three cases, and these "
                   "are checked in code rather than trusted: (1) you have "
                   "already decided this claim in this run - decide once; "
                   "(2) the claim_id does not exist; (3) for an approve, "
                   "lines_resolved does not equal the number of lines on the "
                   "claim, or approved_total + refused_total does not equal "
                   "the sum of the line amounts. Read the error, fix the "
                   "call, do not repeat it unchanged.",
        "irreversible": "YES. This is the one irreversible step in Problem A. "
                        "The gate in front of it is the autonomy setting "
                        "(suggest / confirm / act) in config.py; under "
                        "'confirm' it waits for an operator.",
    },

    "get_clinic_slots": {
        "name": "get_clinic_slots",
        "purpose": "Find appointment slots that actually exist and are free, "
                   "for one specialty in one urgency band inside a date window.",
        "when": "AFTER all four gates pass. Never before - a red flag or a "
                "missing mandatory test ends the run and a slot query at that "
                "point is a wasted call and a wrong record.",
        "args": {
            "specialty": "str, the code from the referral, e.g. 'OPH'",
            "band": "str, REQUIRED, one of urgent|soon|routine, from "
                    "check_referral_criteria - not your own judgement",
            "from/to": "str dates, the window measured from as_of()",
        },
        "returns": "list of {clinic, specialty, band, date, time, "
                   "capacity_remaining}, only rows with capacity above zero",
        "failure": "Returns an EMPTY LIST when nothing is free in that window. "
                   "Empty means escalate - 'no slot in window' - and it does "
                   "NOT mean widen the window or drop the band. A slot with "
                   "capacity_remaining 0 exists and is full; that is a "
                   "different fact from a slot not existing, and neither is a "
                   "reason to book outside the band.",
    },
    "get_preauthorisation": {
        "name": "get_preauthorisation",
        "signature": "get_preauthorisation(member_id: str, procedure_code: str, date_of_service: str) -> Preauthorisation | None",
        "what": "Find evidence that a member's procedure was authorised and valid on the service date.",
        "purpose": "Find a pre-authorisation covering one member for one "
                   "procedure on one date.",
        "when": "ONLY when check_coverage said requires_preauth is true. "
                "Calling it for every line means you did not read the flag.",
        "args": {
            "member_id": "str, from the claim",
            "procedure_code": "str, the line's code",
            "date_of_service": "str date, from the claim - the approval must "
                               "be valid ON this date",
        },
        "returns": "one preauthorisation record <= 5 fields and <= 60 tokens, or None",
        "failure": "Returns None when no approval exists OR when one exists "
                   "but had expired before the date of service. NONE DOES NOT "
                   "MEAN UNCOVERED. It means the evidence is missing, which is "
                   "a REQUEST for the reference - naming the code and the date "
                   "- not a refusal. Deciding otherwise fails the case.",
        "irreversible": "NO. This is a read-only lookup.",
    },
}


# =====================================================================
# THE v1 DESCRIPTOR SET  (D2b) - Huang Yu owns the content
# =====================================================================
# WHAT THIS IS FOR. D2(b) asks us to ship two versions of our tool
# descriptors and MEASURE what the rewrite did - tokens returned per
# call, evaluation pass rate, guardrail cases passed - holding the model
# fixed. The v1 set is the deliberately worse one: the descriptors as a
# team writes them before thinking about the agent-computer interface.
#
# WHY IT IS EMPTY RIGHT NOW, AND WHY THAT IS SAFE. Until this dict is
# populated, prompt.descriptor_set("v1") returns {} and the assembled v1
# prompt differs from v2 - so the hashes differ and nothing silently
# passes. Before this dict existed at all, config.PROMPT_VERSION
# selected NOTHING and sha(v1) == sha(v2): the member running the v1
# pass would have paid for a full battery and produced a file labelled
# v1 containing a v2 run.
#
# evals/run_battery.py refuses to start a v1 battery unless
# sha(v1) != sha(v2) AND every callable tool has a v1 descriptor, so an
# unfinished rewrite costs nothing instead of costing a battery.
#
# HOW TO WRITE IT. Copy DESCRIPTORS above, then make it genuinely worse
# in ways a real team would: drop the size bound from `returns`, replace
# a specific `failure` line with "returns null on error", remove the
# poka-yoke note from check_coverage's policy_id, delete the
# IRREVERSIBLE? field, and let `when` go vague. Do NOT make it worse by
# adding nonsense - the finding is only interesting if v1 is a plausible
# first draft. A rewrite that did not help, honestly reported, scores
# better than one that was never measured.
DESCRIPTORS_V1 = {
    "get_claim": {
        "name": "get_claim",
        "signature": "get_claim(claim_id: str) -> dict",
        "what": "Get the claim record for the supplied id.",
        "when": "Use it first.",
        "args": {"claim_id": "string claim id"},
        "returns": "the claim record, including its line items",
        "failure": "Returns null if the claim cannot be found.",
        "irreversible": "NO",
    },
    "lookup_policy": {
        "name": "lookup_policy",
        "signature": "lookup_policy(member_id: str) -> dict",
        "what": "Get the policy associated with a member.",
        "when": "Use after getting the claim.",
        "args": {"member_id": "string member id"},
        "returns": "the member and policy details, including the remaining limit",
        "failure": "Returns null if the member or policy cannot be found.",
        "irreversible": "NO",
    },
    "lookup_hospital": {
        "name": "lookup_hospital",
        "signature": "lookup_hospital(hospital_id: str) -> dict",
        "what": "Get the hospital information.",
        "when": "Use after getting the claim, with other lookups if useful.",
        "args": {"hospital_id": "string hospital id"},
        "returns": "the hospital record and panel status",
        "failure": "Returns null if the hospital cannot be found.",
        "irreversible": "NO",
    },
    "check_coverage": {
        "name": "check_coverage",
        "signature": "check_coverage(code: str, policy_id: str, documents_attached: list[str] | None = None) -> dict",
        "what": "Check whether a procedure is covered.",
        "when": "Use for each line after finding the policy.",
        "args": {"code": "string procedure code", "policy_id": "string policy id", "documents_attached": "the claim documents, if available"},
        "returns": "coverage, exclusion, preauthorisation and document information",
        "failure": "Returns null on an invalid or missing procedure or policy.",
        "irreversible": "NO",
    },
    "check_duplicate_claim": {
        "name": "check_duplicate_claim",
        "signature": "check_duplicate_claim(member_id: str, hospital_id: str, date_of_service: str, lines: list[dict]) -> dict | None",
        "what": "Check whether this claim was already decided.",
        "when": "Use before issuing a decision.",
        "args": {"member_id": "string", "hospital_id": "string", "date_of_service": "date string", "lines": "claim lines"},
        "returns": "a matching prior claim or null",
        "failure": "Returns null if there is no matching decided claim.",
        "irreversible": "NO",
    },
    "issue_decision_letter": {
        "name": "issue_decision_letter",
        "signature": "issue_decision_letter(claim_id: str, decision: str, lines_resolved: int, approved_total: int|float, refused_total: int|float = 0) -> dict",
        "what": "Record the decision for the member.",
        "when": "Use after the checks and at the end of the process.",
        "args": {"claim_id": "string", "decision": "one of the three outcomes", "lines_resolved": "number of resolved lines", "approved_total": "approved amount", "refused_total": "refused amount"},
        "returns": "a confirmation or an error",
        "failure": "Returns a blocked result if the gate, claim, totals or duplicate check is not satisfied.",
        "irreversible": "YES - the action is covered by the autonomy gate.",
    },
    "get_preauthorisation": {
        "name": "get_preauthorisation",
        "signature": "get_preauthorisation(member_id: str, procedure_code: str, date_of_service: str) -> dict | None",
        "what": "Look for a procedure authorisation.",
        "when": "Use when the coverage result says it may be needed.",
        "args": {"member_id": "string", "procedure_code": "string procedure code", "date_of_service": "date string"},
        "returns": "the first matching authorisation or null",
        "failure": "Returns null if no usable authorisation is found.",
        "irreversible": "NO",
    },
}


def _validate_text(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise TypeError("%s must be a string" % field)
    if not value.strip():
        raise ValueError("%s must not be empty" % field)


def _validate_procedure_code(value: Any) -> None:
    """Runtime boundary validation for the typed procedure-code contract."""
    _validate_text(value, "procedure_code")
    known = {row["code"] for row in _load("A", "procedures")}
    if value not in known:
        raise ValueError("unknown procedure_code %r" % value)


def _validate_iso_date(value: Any, field: str) -> None:
    _validate_text(value, field)
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD)" % field)


def _is_non_negative_number(value: Any) -> bool:
    return (not isinstance(value, bool)
            and isinstance(value, (int, float))
            and value >= 0)


def call(problem, name, args):
    """Dispatch a tool call by name.

    WATCH OUT      unknown tool names fail LOUDLY. A silent no-op here
                   would produce a run that looks fine and decided
                   nothing on evidence it never gathered - the most
                   expensive kind of bug in this assignment, because
                   nothing about the output says anything went wrong.
    """
    table = REGISTRY[problem]
    if name not in table:
        raise KeyError(
            "No tool named %r for Problem %s. Available: %s"
            % (name, problem, ", ".join(sorted(table))))
    try:
        return table[name](**args)
    except (TypeError, ValueError) as exc:
        # Keep a bad model call inside the observable transcript while
        # retaining the direct function's runtime enforcement.
        return {"status": "ERROR", "error": "INVALID_ARGUMENTS",
                "detail": str(exc)}
