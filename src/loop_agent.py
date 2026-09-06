"""
PE6201 · A2 scaffold — THE AGENT LOOP  (D1)
====================================================================
    thought -> action -> observation -> repeat -> final

That is the whole of ReAct, and it is hand-rolled here on purpose. No
framework owns your loop: when it misbehaves you need to be able to
read the twelve lines that did it.

WHAT MAKES THIS AN AGENT RATHER THAN A WORKFLOW: the number of steps is
decided by the DATA, not by you. A one-line claim with a live policy is
a short run. A four-line claim with a pre-authorisation to chase is a
long one. You did not write that branch - the record did.

--------------------------------------------------------------------
INSTRUMENTATION IS NOT OPTIONAL

Every run records turns, tokens, cost, every tool call and every
guardrail event. D6's cost model and D7's loop failure both need
numbers that were captured WHILE THE RUN HAPPENED. A team that adds
instrumentation afterwards has to run the whole battery again.

You cannot report a failure you had no way of noticing.
====================================================================
"""
import time

import config
import prompt
from tools import tools
from backends.backends import LiveTransportError, make_backend
from backends.guardrails import Guardrails, GuardrailStop


def run_case(case_id, problem=None, approve=None, verbose=False):
    """Run ONE case from a clean state and return the decision record.

    ISOLATION (D4): everything this function needs is created inside it.
    No case may depend on a previous one having run - so no module-level
    counters, no shared guardrail object, no leftover transcript.
    """
    problem = problem or config.PROBLEM
    started = time.time()

    # Clear the gated action's once-only memory. This is what keeps the
    # guard per-RUN rather than per-process: negative cases get three
    # trials each, so the same claim is legitimately decided three times
    # in one process and a persistent guard would block trials 2 and 3.
    tools.reset_decision_state()

    guards = Guardrails(config.MAX_TURNS, config.MAX_TOKENS_PER_RUN,
                        config.AUTONOMY)
    # WHAT THE MODEL IS TOLD. On the scripted backend these are ignored -
    # the moves are pre-written, so no prompt is ever sent. On the live
    # backend this IS the experiment D2(b) measures: the descriptors and
    # the routing rules, assembled by prompt.build_system_prompt().
    #     python3 run_eval.py --prompt      to see the exact text
    backend = make_backend(
        case_id,
        tool_descriptors=[tools.DESCRIPTORS[n] for n in tools.REGISTRY[problem]
                          if n in tools.DESCRIPTORS],
        system_prompt=prompt.build_system_prompt(problem))

    transcript = []      # what the model would see
    evidence = []        # every tool actually called, in order

    # TURNS ARE TOOL-CALLING TURNS. The concluding move - where the agent
    # writes its decision record - is bookkeeping, not a turn. This is the
    # same convention Appendix A uses: CLM-8842 is "turns": 4 with EIGHT
    # tool calls, because the gated action is a turn like any other and
    # the write-up afterwards is not. Count them any other way and your
    # D2(c) arithmetic stops agreeing with the brief.
    turns = 0
    iterations = 0       # loop-safety only; never reported
    tokens_in = tokens_out = 0
    stopped_by = None
    # PER-TURN tokens, not just the run total. Two things need this and
    # neither can be recovered afterwards: reasoning-spike detection
    # becomes a pure function over a saved record, and the B and D terms
    # of  input ~ B*T + D*T(T-1)/2  can be read off directly, per model.
    turn_tokens = []

    # On the scripted backend the gate auto-approves so the run stays
    # deterministic. The RECORD still shows the gate was reached and
    # passed, which is what a marker looks for.
    if approve is None:
        approve = lambda action, payload: True

    try:
        while True:
            iterations += 1
            if iterations > config.MAX_TURNS + 2:
                raise GuardrailStop("step_cap", "loop did not terminate")

            move = backend.next_move(transcript)
            ti, to = backend.token_estimate(transcript)
            tokens_in, tokens_out = tokens_in + ti, tokens_out + to
            turn_tokens.append([ti, to])
            guards.check_budget(tokens_in + tokens_out)

            if verbose:
                label = ("conclude" if "final" in move else "turn %d" % (turns + 1))
                print("  %-9s · %s" % (label, move.get("thought", "")[:88]))

            # ---- conclude -------------------------------------------
            if "final" in move:
                record = dict(move["final"])
                break

            # ---- act: one turn may carry SEVERAL calls ---------------
            turns += 1
            guards.check_turns(turns)

            # Only calls INDEPENDENT of each other belong in one turn.
            # A dependency chain cannot be shortened by running things at
            # once - that is why Problem B saves less than Problem A.
            calls = move.get("calls") or [(move["tool"], move["args"])]
            observations = []

            for name, args in calls:
                guards.check_duplicate(name, args)

                # THE GATE goes in front of the irreversible step only.
                if name == tools.GATED_ACTION.get(problem):
                    if not guards.gate(name, args, approve):
                        raise GuardrailStop(
                            "gate_held",
                            "%s awaits human approval (autonomy=%s)"
                            % (name, config.AUTONOMY))

                # A HALLUCINATED TOOL NAME MUST NOT KILL THE BATTERY.
                # tools.call raises KeyError on an unknown name and
                # TypeError on wrong arguments - both are things a live
                # model does. Uncaught, either one propagates out of
                # run_case, out of the harness loop, and ends a paid
                # 88-trial run partway through with no results file.
                #
                # The error becomes the OBSERVATION instead: the agent
                # reads what it did wrong and gets a chance to correct,
                # exactly as it would from any other tool result. The
                # call still enters `evidence`, because a trace that
                # hides the bad call cannot be used to diagnose it.
                try:
                    result = tools.call(problem, name, args)
                except KeyError as err:
                    result = {"error": "no such tool: %s" % err}
                except TypeError as err:
                    result = {"error": "wrong arguments for %s: %s"
                                       % (name, err)}
                evidence.append(name)
                observations.append({"tool": name, "args": args,
                                     "observation": result})
                if verbose:
                    print("       %-26s -> %s" % (name, _short(result)))

            transcript.append({"role": "assistant",
                               "content": move.get("thought", "")})
            transcript.append({"role": "user",
                               "content": repr(observations)})

    except GuardrailStop as stop:
        # A LOUD STOP. The record says what halted the run and where, so
        # this never looks like a quiet wrong answer.
        stopped_by = stop.reason
        record = {"decision": "escalate",
                  "reason": "halted by the %s guardrail - %s"
                            % (stop.reason, stop.detail)}

    except LiveTransportError as err:
        # NOT a model failure, and the distinction is worth money. The
        # tokens already spent on turns 1..n-1 of this run are real; if
        # this exception escaped run_case it would unwind through the
        # harness and that spend would go unrecorded. Handled here, the
        # record below still carries the accumulated counts.
        #
        # `stopped_by == "transport"` is what tells the battery aggregator
        # to leave this trial OUT of the pass-rate denominator and report
        # it in its own column. A network problem is not evidence about a
        # model.
        stopped_by = "transport"
        record = {"decision": "escalate",
                  "reason": "transport failure, not a model answer - %s"
                            % err}

    cost = (tokens_in / 1e6) * config.PRICE_IN + (tokens_out / 1e6) * config.PRICE_OUT

    record.update({
        "case_id": case_id,
        "evidence": evidence,
        "turns": turns,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost, 6),
        "seconds": round(time.time() - started, 3),
        "turn_tokens": turn_tokens,
        "guardrails_fired": guards.fired,
        "stopped_by": stopped_by,
        "backend": backend.name,
    })
    if backend.name == "live":
        record.update({
            "model": config.MODEL,
            "prompt_version": config.PROMPT_VERSION,
            "served_model": (backend.last_meta or {}).get("served_model"),
            "provider": (backend.last_meta or {}).get("provider"),
            "usage_complete": backend.usage_seen,
            "turn_usage": backend.turn_usage,
        })
    return record


def _short(value, n=64):
    s = repr(value)
    return s if len(s) <= n else s[:n - 1] + "…"
