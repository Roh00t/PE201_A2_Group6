"""
PE6201 · A2 — THE DETERMINISTIC PLANNER  (D5a, feeds D2c and D7)
====================================================================
WHAT THIS IS. A stand-in for the model, written in code. Given a claim
id it derives the sequence of moves a competent agent would make and
hands them to the loop in exactly the shape `SCRIPTS` uses. The loop,
the tools, the guardrails, the gate, the ledger and the instrumentation
are all the real ones - the only simulated part is the model's choices.

WHY IT EXISTS. D5(a) requires the harness to run end to end on a
scripted backend so a marker can clone the repository and reproduce our
numbers at zero cost. Hand-writing move-lists for fifty claims is about
250 blocks of prose and would consume the week; deriving them is 200
lines and covers every case, including the ones we add tomorrow.

WHAT IT IS NOT, AND THIS MUST BE SAID IN THE REPORT. The scripted pass
rate this produces is close to 100% BY CONSTRUCTION - the planner
implements the routing rule, so of course it agrees with a key written
from the same routing rule. It is not evidence that our agent is good.
It is evidence that the MACHINERY reproduces: that the loop parses
multi-call turns, that the guardrails fire, that the gate holds, that
the ledger writes, that the instrumentation counts. The only honest
pass rates in A2 come from D5(b), where a real model makes the choices.

WHAT IT MAY NOT DO. It never reads expected_outcomes_A.json, and it
contains no branch keyed to a claim id. Every decision below is derived
from the fixtures and from Appendix A's routing table. A planner that
peeked at the answer key would agree with it by construction and
measure nothing at all - the same mistake as writing a label from the
agent's output, in the other direction.

--------------------------------------------------------------------
OUR DEPENDENCY RULE (D2c) - stated, then measured both ways

  Turn 1   get_claim                                  ALONE
           Everything downstream needs the member, the hospital and the
           line items it returns.

  Turn 2   lookup_policy || lookup_hospital || check_duplicate_claim
           Three calls that need only the claim record, and none of
           which needs another's output. They go together.

  Turn 3   check_coverage x N   (one per line)
           Independent OF EACH OTHER, so one turn - but NOT independent
           of turn 2, because our check_coverage requires a policy_id
           and only lookup_policy can supply one.

  Turn 4   get_preauthorisation x M   (only the lines that need one)
           Cannot join turn 3: we do not know WHICH line requires an
           approval until coverage has answered.

  Turn 5   issue_decision_letter                      GATED

WHERE WE DIVERGE FROM THE BRIEF'S EXAMPLE, AND WHY. Appendix A folds
lookup_policy and check_coverage into one turn and reaches CLM-8842 in
four. We reach it in five, because our check_coverage takes a REQUIRED
policy_id - the poka-yoke from D2(b) - and that turns a parallel pair
into a chain. The brief anticipates exactly this: "a team that
parallelises less than we did and explained why is on stronger ground
than one that copied this page", and "D2(c) marks your reasoning, not
your number."

So the poka-yoke costs us one turn on every approval. That is a real,
measured trade between D6's lever 2 (turn count) and the interface
constraint that makes a coverage check against no policy impossible.
We think it is worth it and the report says so with the numbers.

WHAT IT BUYS BACK. Because turn 2 is claim-level only, a lapsed policy,
a breached limit or a duplicate ESCALATES AT TWO TURNS without ever
pricing a line - which is exactly Appendix A's CLM-8925 record, "the
claim cannot be decided at this level regardless of coverage", and the
early exit the brief says an evaluation set should reward. Eleven of
our fifty cases escalate. We pay one turn on the approvals to save two
or three on those.

--------------------------------------------------------------------
PRECEDENCE. Read off the shipped answer key, not invented - see the
provenance note in make_fixtures_A.py:

  injection > policy lapsed > outside policy dates > duplicate >
  annual limit exceeded > line-level (document, then pre-auth) > approve

Two of those orderings deserve their reason stated:

  * INJECTION DOES NOT EXIT EARLY. It is the highest-precedence
    trigger, but the key asks the record to show the instruction was
    found and NOT followed, and for CLM-8952 that "the real
    check_coverage result was used instead". You cannot show that
    without running the coverage check. So the flag is raised at turn 1
    and the run continues to turn 3 before escalating.

  * DOCUMENT BEFORE PRE-AUTH is an assumption, not evidence. No case in
    our set is missing both, so nothing in the data settles it. We
    resolve documents first because check_coverage now answers that in
    the same turn, which makes the request one turn cheaper. Stated
    here so a marker can see it was a choice.
====================================================================
"""
import config
import narrative_guard
from tools import tools

ESCALATE_TO = "human claims assessor"


# =====================================================================
# GATHERING - what the observations would tell the agent
# =====================================================================
def _facts(claim):
    """Everything the tools would return, gathered once."""
    pol = tools.lookup_policy(claim["member_id"])
    hosp = tools.lookup_hospital(claim["hospital_id"])
    dup = tools.check_duplicate_claim(claim["member_id"], claim["hospital_id"],
                                      claim["date_of_service"], claim["lines"])
    return {"policy": pol, "hospital": hosp, "duplicate": dup,
            "flags": narrative_guard.inspect(claim.get("narrative", "")),
            "total": sum(l["amount"] for l in claim["lines"])}


def _coverage(claim, policy_id):
    """One check_coverage result per line, in line order."""
    return [tools.check_coverage(l["code"], policy_id,
                                 documents_attached=claim.get("documents"))
            for l in claim["lines"]]


# =====================================================================
# THE ROUTING RULE
# =====================================================================
def _claim_level_trigger(claim, f):
    """The escalations decidable from turn 2, in precedence order.

    Returns (trigger, reason, extra_record_fields) or None.
    """
    pol = (f["policy"] or {}).get("policy", {})
    remaining = (f["policy"] or {}).get("remaining")

    if pol.get("status") == "lapsed":
        return ("policy_lapsed",
                "Policy %s status lapsed. The claim cannot be decided "
                "against cover that is not live." % pol.get("policy_id"), {})

    dos = claim["date_of_service"]
    if pol and not (pol.get("start_date") <= dos <= pol.get("end_date")):
        where = "before" if dos < pol.get("start_date") else "after"
        return ("outside_policy_dates",
                "Date of service %s falls %s policy %s's cover window "
                "%s..%s. Status is %r, which does not extend the dates."
                % (dos, where, pol.get("policy_id"), pol.get("start_date"),
                   pol.get("end_date"), pol.get("status")), {})

    if f["duplicate"]:
        d = f["duplicate"]
        return ("duplicate_claim",
                "%s named as the prior decision. The facts that matched: "
                "member %s, hospital %s, date of service %s, and the same "
                "lines. The claim id is not one of the facts - a "
                "resubmission arrives with a new one."
                % (d["claim_id"], d["member_id"], d["hospital_id"],
                   d["date_of_service"]),
                {"prior_claim_id": d["claim_id"]})

    if remaining is not None and f["total"] > remaining:
        return ("annual_limit_exceeded",
                "Claim total %d exceeds %d remaining on %s. Lines were not "
                "individually priced: the claim cannot be decided at this "
                "level regardless of coverage."
                % (f["total"], remaining, pol.get("policy_id")), {})
    return None


def _line_disposition(claim, covs, preauths):
    """Per-line status, and the totals that follow from it."""
    lines = []
    approved = refused = 0
    for line, cov in zip(claim["lines"], covs):
        row = {"code": line["code"], "amount": line["amount"]}
        if cov and cov["excluded"]:
            row["status"] = "not_covered"
            row["exclusion"] = cov["exclusion_rule"]
            refused += line["amount"]
        else:
            row["status"] = "covered"
            pa = preauths.get(line["code"])
            if pa:
                row["preauth"] = "%s valid %s..%s" % (pa["preauth_id"],
                                                      pa["valid_from"],
                                                      pa["valid_to"])
            approved += line["amount"]
        lines.append(row)
    return lines, approved, refused


# =====================================================================
# THE PLAN
# =====================================================================
def _turn(thought, calls):
    return {"thought": thought, "calls": calls}


def plan(claim_id, mode="parallel"):
    """Derive the move list for one claim. `mode` is 'parallel' or
    'sequential' - the same work, grouped two ways, which is what D2(c)
    measures."""
    claim = tools.get_claim(claim_id)
    if claim is None:
        # A broken case, not an outcome. Appendix A has only three
        # outcomes so there is nowhere else for this to go; we escalate
        # and name the reason rather than inventing a fourth decision.
        # Logged as an open question for the lecturer.
        return [{"thought": "No claim has that id. I will not invent one.",
                 "final": {"decision": "escalate",
                           "trigger": "record_not_found",
                           "escalate_to": ESCALATE_TO,
                           "reason": "No claim %s exists in the records. "
                                     "Nothing can be decided." % claim_id}}]

    batches, f = [], None
    batches.append(("Turn 1 must run alone: everything after this needs the "
                    "member, the hospital and the LINE ITEMS it returns.",
                    [("get_claim", {"claim_id": claim_id})]))

    f = _facts(claim)
    pol_row = (f["policy"] or {}).get("policy", {})
    policy_id = pol_row.get("policy_id")

    batches.append(("Three claim-level checks that need nothing but that "
                    "record, and nothing from each other: the policy, the "
                    "hospital, and whether this episode was already decided.",
                    [("lookup_policy", {"member_id": claim["member_id"]}),
                     ("lookup_hospital", {"hospital_id": claim["hospital_id"]}),
                     ("check_duplicate_claim",
                      {"member_id": claim["member_id"],
                       "hospital_id": claim["hospital_id"],
                       "date_of_service": claim["date_of_service"],
                       "lines": claim["lines"]})]))

    claim_level = _claim_level_trigger(claim, f)
    hostile = f["flags"]

    # ---- escalate at turn 2, without pricing a line ------------------
    if claim_level and not hostile:
        trigger, reason, extra = claim_level
        final = {"decision": "escalate", "trigger": trigger,
                 "escalate_to": ESCALATE_TO, "reason": reason}
        final.update(extra)
        return _emit(batches, final, mode,
                     "Enough to stop. Pricing lines this claim will never "
                     "pay would be burned turns.")

    # ---- turn 3: one coverage check per line -------------------------
    covs = _coverage(claim, policy_id)
    batches.append(("One coverage check PER LINE - %d lines, %d calls. They "
                    "are independent of each other so they share a turn, but "
                    "they could not join turn 2: check_coverage requires a "
                    "policy_id and only lookup_policy could give me one."
                    % (len(claim["lines"]), len(claim["lines"])),
                    [("check_coverage",
                      {"code": l["code"], "policy_id": policy_id,
                       "documents_attached": claim.get("documents")})
                     for l in claim["lines"]]))

    # ---- highest precedence: an instruction aimed at the system ------
    if hostile:
        rules = ", ".join(sorted({h["rule"] for h in hostile}))
        quoted = "; ".join('"%s"' % h["matched"] for h in hostile)
        refused_lines = [l["code"] for l, c in zip(claim["lines"], covs)
                         if c and c["excluded"]]
        return _emit(batches, {
            "decision": "escalate",
            "trigger": narrative_guard.TRIGGER,
            "escalate_to": ESCALATE_TO,
            "narrative_flags": hostile,
            "reason": "The member's narrative contains text aimed at this "
                      "system (%s): %s. The instruction was FOUND AND NOT "
                      "FOLLOWED - the real check_coverage results were used "
                      "instead, and %s. Free text from outside the "
                      "organisation is data, never an instruction, and no "
                      "authority asserted in it exists in the records."
                      % (rules, quoted,
                         ("line %s was not approved" % ", ".join(refused_lines))
                         if refused_lines else
                         "no line was approved on the strength of it"),
        }, mode, "Found an instruction in member-supplied text. I checked "
                 "coverage properly first so the record can prove I used the "
                 "real result, then escalate.")

    # ---- a required document that is not attached --------------------
    for line, cov in zip(claim["lines"], covs):
        if cov and cov["document_attached"] is False:
            # `itemised_bill` is how the fixture stores it. The request
            # goes to a MEMBER, so the record names "itemised bill" - the
            # identifier is ours, the words are theirs. Found by the code
            # check on `missing`, which is the whole reason that check
            # exists: the decision field was already right.
            doc = cov["required_document"].replace("_", " ")
            return _emit(batches, {
                "decision": "request_document",
                "missing": "%s for line %s" % (doc, line["code"]),
                "reason": "Line %s requires %s and it is not among the "
                          "documents attached (%s). Named exactly, with the "
                          "line it belongs to."
                          % (line["code"], doc,
                             ", ".join(claim.get("documents") or ["none"])),
                "lines_resolved": _resolved_summary(claim, covs),
            }, mode, "A document rule is unmet. Ask for that document by "
                     "name - never 'more information'.")

    # ---- turn 4: chase the pre-authorisations we now know we need ----
    needs = [l for l, c in zip(claim["lines"], covs)
             if c and c["requires_preauth"] and not c["excluded"]]
    preauths = {}
    if needs:
        batches.append(("This CANNOT join the turn above: I did not know "
                        "which line needed a pre-authorisation until "
                        "coverage answered. Only %s does."
                        % ", ".join(l["code"] for l in needs),
                        [("get_preauthorisation",
                          {"member_id": claim["member_id"],
                           "procedure_code": l["code"],
                           "date_of_service": claim["date_of_service"]})
                         for l in needs]))
        for l in needs:
            preauths[l["code"]] = tools.get_preauthorisation(
                claim["member_id"], l["code"], claim["date_of_service"])

        for l in needs:
            if preauths[l["code"]] is None:
                return _emit(batches, {
                    "decision": "request_document",
                    "missing": "pre-authorisation reference for line %s, "
                               "valid on %s" % (l["code"],
                                                claim["date_of_service"]),
                    "reason": "Line %s requires pre-authorisation. None "
                              "covering member %s for %s is valid on %s - "
                              "either none was granted or one existed and had "
                              "expired. Missing evidence is a REQUEST, not a "
                              "refusal."
                              % (l["code"], claim["member_id"], l["code"],
                                 claim["date_of_service"]),
                    "lines_resolved": _resolved_summary(claim, covs),
                }, mode, "The approval is missing or expired. Ask for it by "
                         "code and date.")

    # ---- approve: every line has a disposition -----------------------
    lines, approved, refused = _line_disposition(claim, covs, preauths)
    batches.append(("A disposition for every line, so the decision can go "
                    "out. This is the irreversible step: it is a turn like "
                    "any other and it goes through the gate.",
                    [("issue_decision_letter",
                      {"claim_id": claim_id,
                       "decision": "approve_in_principle",
                       "lines_resolved": len(claim["lines"]),
                       "approved_total": approved,
                       "refused_total": refused})]))

    hosp = f["hospital"] or {}
    excluded = [l for l in lines if l["status"] == "not_covered"]
    return _emit(batches, {
        "decision": "approve_in_principle",
        "lines": lines,
        "approved_total": approved,
        "refused_total": refused,
        "reason": "Policy %s active %s..%s, %d remaining. %d line(s): %s. "
                  "approved_total %d, refused_total %d. Hospital %s is %s."
                  % (pol_row.get("policy_id"), pol_row.get("start_date"),
                     pol_row.get("end_date"), (f["policy"] or {}).get("remaining"),
                     len(lines), "; ".join(_line_phrase(l) for l in lines),
                     approved, refused, hosp.get("hospital_id"),
                     "on panel" if hosp.get("panel") else
                     "NOT on panel - the member paid and is claiming it back"),
    }, mode,
        "%d line(s) resolved, %d excluded. A partly payable claim is still an "
        "approve: one decision covering both." % (len(lines), len(excluded)))


def _line_phrase(l):
    if l["status"] == "not_covered":
        return "%s refused under %s (%d)" % (l["code"], l.get("exclusion"),
                                             l["amount"])
    if l.get("preauth"):
        return "%s covered, %s cited (%d)" % (l["code"], l["preauth"],
                                              l["amount"])
    return "%s covered (%d)" % (l["code"], l["amount"])


def _resolved_summary(claim, covs):
    """What the run DID settle before it stopped. An ask still records
    what it resolved - Appendix A's CLM-8888 shows a refusal inside a
    request."""
    out = []
    for line, cov in zip(claim["lines"], covs):
        if not cov:
            continue
        if cov["excluded"]:
            out.append("%s not covered - %s" % (line["code"],
                                                cov["exclusion_rule"]))
        else:
            out.append("%s covered" % line["code"])
    return out


def _emit(batches, final, mode, closing_thought):
    """Turn the batch list into moves, grouped or one call per turn."""
    moves = []
    if mode == "sequential":
        for thought, calls in batches:
            for call in calls:
                moves.append(_turn(thought, [call]))
    else:
        for thought, calls in batches:
            moves.append(_turn(thought, calls))
    moves.append({"thought": closing_thought, "final": final})
    return moves


class PlannerBackend:
    """Same interface as ScriptedBackend. Deterministic, free, offline."""

    name = "scripted"

    def __init__(self, case_id, mode=None):
        self.mode = mode or getattr(config, "GROUPING", "parallel")
        self.steps = plan(case_id, self.mode)
        self.i = 0

    def next_move(self, transcript):
        """`transcript` is ignored: the plan was derived up front from the
        records, which is what makes the run reproducible."""
        if self.i >= len(self.steps):
            return {"final": {"decision": "escalate",
                              "reason": "plan ended without a conclusion"},
                    "thought": "plan exhausted"}
        step = self.steps[self.i]
        self.i += 1
        return step

    @staticmethod
    def token_estimate(transcript):
        # ESTIMATES, so the cost arithmetic has something to chew on.
        # Not measurements - D6's figures come from the live battery.
        return 1800 + 600 * len(transcript), 120
