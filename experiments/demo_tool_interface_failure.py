#!/usr/bin/env python3
"""
PE6201 · A2 — D7 FAILURE 2: the tool interface
====================================================================
    python3 experiments/demo_tool_interface_failure.py

Failure 1 (demo_loop_failure.py) is loop control. D7 requires the
second failure to sit in a DIFFERENT layer, so this one is the tool
interface - and, like failure 1, it is built as a DELETION from the
working agent rather than as a separately written bad agent.

WHAT IS DELETED
    check_coverage currently answers four questions in one call:
        is this line covered · is it excluded · does it need a pre-auth
        · IS A DOCUMENT REQUIRED, AND IS IT ATTACHED
    The last one is the widening. Appendix A's suggested interface did
    not have it; we added it rather than adding a get_required_documents
    tool, and D2(a) records that as a "we tried not adding one".

    Here we take it back out. The narrowed tool still returns
    `required_document` and `document_attached`, but always as None -
    which is exactly what the caller sees when the interface has no way
    of knowing. Nothing else changes.

WHY THIS IS THE INTERESTING FAILURE
    It does not crash. It does not loop. It does not breach a cap. The
    agent reads `document_attached: None`, cannot distinguish "no
    document is required" from "we never looked", falls through to the
    approve branch, and COMMITS THE INSURER to a claim that should have
    been held for an itemised bill.

    A silent wrong answer, in the expensive direction. The step cap,
    the budget ceiling and the de-duplication guard all stay quiet,
    because none of them is breached - the run is short, cheap and
    internally consistent. Only the answer key disagrees.

Runs on the SCRIPTED backend. Free, deterministic, no key.
====================================================================
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config                                     # noqa: E402
import tools                                      # noqa: E402  (the package)
from tools import tools as tools_mod              # noqa: E402  (the module)
from evals import harness                         # noqa: E402

# The one case in the set whose correct outcome turns on a required
# document. Chosen from the answer key, not from what the agent did.
CASE = "CLM-8901"


# THE TOOL IS REACHED BY TWO ROUTES and a deletion has to close both.
# The loop dispatches through tools.REGISTRY["A"]["check_coverage"],
# which holds the function OBJECT; the scripted planner calls the module
# attribute tools.tools.check_coverage. Patching only one of them
# produces a demo that proves nothing while looking like it ran - which
# is itself the D7 lesson, arriving early and at our own expense.
_REAL = tools.REGISTRY["A"]["check_coverage"]


def narrowed_check_coverage(code, policy_id, documents_attached=None):
    """check_coverage as it was BEFORE the widening.

    The signature is kept so nothing else has to change - this is a
    deletion of what the tool KNOWS, not of how it is called. Both
    document fields come back None: the honest answer from an interface
    that was never given the claim's documents to compare against.
    """
    result = _REAL(code, policy_id, documents_attached)
    if result is None:
        return None
    result = dict(result)
    result["required_document"] = None
    result["document_attached"] = None
    return result


def run_whole_set():
    """Pass rate over the full set, both ways. One case is an anecdote."""
    return harness.run_set(problem="A")


def summarise(res):
    """harness.run_set returns (results, judgement_queue)."""
    trials = res[0]
    passed = sum(1 for r in trials if r["passed"])
    return passed, len(trials)


def one_case(case_id):
    from loop_agent import run_case
    tools.reset_decision_state()
    return run_case(case_id, problem="A")


def main():
    print()
    print(config.summary())
    print("  demonstrating on %s (Problem A)" % CASE)
    print()

    # ---- BEFORE: the working agent ---------------------------------
    before = one_case(CASE)
    before_set = summarise(run_whole_set())
    print("BEFORE - the working agent, check_coverage widened")
    print("  turns %d · tool calls %d · cost US$%.5f · decision %s"
          % (before["turns"], len(before["evidence"]), before["cost_usd"],
             before["decision"]))
    print("  missing: %r" % before.get("missing"))
    print("  whole set: %d of %d trials passed" % before_set)

    # ---- AFTER: the same agent, MINUS the widening ------------------
    tools.REGISTRY["A"]["check_coverage"] = narrowed_check_coverage
    tools_mod.check_coverage = narrowed_check_coverage
    try:
        after = one_case(CASE)
        after_set = summarise(run_whole_set())
    finally:
        tools.REGISTRY["A"]["check_coverage"] = _REAL     # <- put it back
        tools_mod.check_coverage = _REAL

    print()
    print("AFTER - the working agent MINUS the check_coverage widening")
    print("  turns %d · tool calls %d · cost US$%.5f · decision %s"
          % (after["turns"], len(after["evidence"]), after["cost_usd"],
             after["decision"]))
    print("  missing: %r" % after.get("missing"))
    print("  stopped by: %s" % after["stopped_by"])
    print("  whole set: %d of %d trials passed" % after_set)

    # ---- what D7 asks you to report --------------------------------
    print()
    print("=" * 68)
    print("  1 · HOW IT WAS DETECTED")
    print("      NOT by an exception, a cap or a cost spike. The broken")
    print("      run is %d turns and US$%.5f against %d turns and US$%.5f"
          % (after["turns"], after["cost_usd"], before["turns"],
             before["cost_usd"]))
    print("      for the correct one - one turn LONGER, because approving")
    print("      has to pass the gate and requesting a document stops")
    print("      before it. So the broken run is the more expensive one,")
    print("      and a cost alarm would have fired on the CORRECT")
    print("      behaviour. Every guardrail stayed silent: stopped_by is")
    print("      %r." % after["stopped_by"])
    print("      It was caught by the CODE CHECK in D4, comparing")
    print("      `decision` against the answer key - which is why D4")
    print("      grades the outcome and not the transcript, and why a")
    print("      turns-and-cost alarm is not a correctness instrument.")
    print()
    print("  2 · BEFORE AND AFTER, ON THE WHOLE SET")
    print("      pass rate   %d/%d  ->  %d/%d   (%+.1f pp)"
          % (before_set[0], before_set[1], after_set[0], after_set[1],
             100.0 * (after_set[0] / after_set[1] - before_set[0] / before_set[1])))
    print("      decision    %s  ->  %s" % (before["decision"], after["decision"]))
    print("      turns/run   %d  ->  %d" % (before["turns"], after["turns"]))
    print("      cost/run    US$%.5f  ->  US$%.5f"
          % (before["cost_usd"], after["cost_usd"]))
    print("      %d trials moved, all of them the same case run three"
          % (before_set[0] - after_set[0]))
    print("      times: %s is a NEGATIVE case, so the 3x trial policy" % CASE)
    print("      turns one interface defect into three failed trials.")
    print("      That is the policy earning its cost - a single trial")
    print("      would have made this a coin-flip finding.")
    print("      It matters out of proportion to its size because of")
    print("      layer 2: at 8,000 claims a month a wrongly approved")
    print("      claim costs US$7.60 of assessor time to unwind, and")
    print("      unlike a refusal it has already committed the insurer.")
    print()
    print("  3 · WHICH LAYER THE FIX BELONGS IN, AND WHY THE OTHER TWO")
    print("      ARE WRONG")
    print()
    print("      TOOL INTERFACE - correct. The information the decision")
    print("      needs was never returned. check_coverage sees the policy")
    print("      and the claim's documents, so it is the only place that")
    print("      CAN answer 'is the required document attached'. Widening")
    print("      one return is also cheaper than a get_required_documents")
    print("      tool: a new tool adds a descriptor to the prefix that is")
    print("      re-billed on every turn whether or not it is called.")
    print()
    print("      LOOP CONTROL - wrong, and this is the instructive part.")
    print("      Every guard behaved correctly. Nothing repeated, nothing")
    print("      ran long, nothing overspent. A cap cannot detect a fault")
    print("      that makes the run SHORTER. Tightening the caps here")
    print("      would punish the correct runs and leave this one alone.")
    print()
    print("      PROMPT - wrong, and the most tempting. You cannot")
    print("      instruct a model to take account of a field the tool")
    print("      never returned. 'Always check whether a document is")
    print("      required' produces a model that says it checked. That is")
    print("      the difference between a guardrail and a wish, and it is")
    print("      the same reason D3(a) puts the four guards in code.")
    print("=" * 68)
    print()


if __name__ == "__main__":
    sys.exit(main() or 0)
