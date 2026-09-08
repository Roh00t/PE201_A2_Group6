# D7 · Two reproduced failures

Owner: Xia Yanran (reproductions) · Rohit Panda (instrumentation)
Backend: `scripted` for both. **Neither failure costs a token.** `[brief §7]`

Both failures are built as a **deletion from the working agent** — "the working
agent, minus X" — not as a separately written bad agent. Putting X back recovers
the behaviour, which is what makes each one a diagnosis rather than a story.
`[faq]`

```bash
python3 experiments/demo_loop_failure.py             # failure 1 · loop control
python3 experiments/demo_tool_interface_failure.py   # failure 2 · tool interface
```

---

## Failure 1 — loop control · action de-duplication deleted

`experiments/demo_loop_failure.py` · demonstrated on `CLM-8842`

**What is deleted.** `Guardrails.check_duplicate` becomes a no-op. The script
repeats one call the agent has already made — a model that has forgotten it
already asked. Everything else is untouched.

### The instrumentation that found it

Nothing raised an exception. Nothing hit a cap. The run **returned the correct
answer**:

| | turns | tool calls | tokens | cost | decision | stopped_by |
|---|---:|---:|---:|---:|---|---|
| before | 5 | 8 | 29,520 | US$0.00317 | `approve_in_principle` | — |
| after | 7 | 12 | 48,960 | US$0.00518 | `approve_in_principle` | `None` |

**1.66× the cost for the same answer.** A pass-rate table alone scores this run as
a clean pass. It is visible only because turns and cost are logged per run — which
is the entire argument for instrumenting before measuring. *You cannot report a
failure you had no way of noticing.* `[faq]`

### Turn distribution across the whole set

One number is not a distribution. `experiments/d2c_parallel_vs_sequential.py`
prints this over all 60 trials, parallel grouping:

| turns | runs |
|---:|---|
| 2 | 12 |
| 3 | 12 |
| 4 | 29 |
| 5 | 7 |

median **4** · mean 3.52 · **worst legitimate 5** · hit the cap **0**

**This is where the step cap comes from.** `MAX_TURNS = 8` is the worst
legitimate run plus three turns for a model that wanders once and recovers. A cap
of 30 would be decoration; a cap of 5 would truncate the longest correct run in
the set. The budget ceiling is derived the same way from measured per-run cost.

### Which guard caught it, and why the other two could not

- **Action de-duplication — caught it.** It is the only guard that holds a memory
  of what the agent has already done.
- **The step cap never fired.** The broken run finished at 7 turns inside a cap of
  8. A cap *bounds* the damage; it does not *detect* the fault. One more repeated
  call and it would fire — later, and still without naming the cause.
- **The budget ceiling never fired.** 48,960 tokens against a ceiling of 60,000.
- **A prompt fix cannot be relied on.** The model is the thing that forgot. Only
  the code layer remembers. This is why D3(a) puts all four guards in code.

### Pass rate did not fall when the guard was restored

A step cap that stops a runaway also truncates a legitimate long run. Restoring
the guard leaves the set at **60/60**, and `d2c_parallel_vs_sequential.py`
confirms **0 of 60** trials reach the cap under the shipped grouping. The caps
bound cost without costing correctness — *under the parallel grouping they were
derived from*. Run the same work one call per turn and 11 trials breach a
ceiling. A cap is only defensible alongside the grouping it was calibrated under,
and that limit is stated rather than hidden.

---

## Failure 2 — tool interface · the `check_coverage` widening deleted

`experiments/demo_tool_interface_failure.py` · demonstrated on `CLM-8901`

**A different layer, as D7 requires** — not loop control again.

**What is deleted.** `check_coverage` currently answers four questions in one
call: covered · excluded · needs a pre-auth · **is a document required, and is it
attached**. The last is the widening D2(a) records as a *"we tried not adding a
tool"*. Here it is taken back out: the narrowed tool still returns
`required_document` and `document_attached`, but always as `None` — exactly what
a caller sees from an interface that was never given the claim's documents.

### What happens

| | turns | tool calls | cost | decision | `missing` | set |
|---|---:|---:|---:|---|---|---|
| before | 3 | 5 | US$0.00163 | `request_document` | `itemised bill for line 45378` | **60/60** |
| after | 4 | 6 | US$0.00234 | `approve_in_principle` | `None` | **57/60** |

The agent reads `document_attached: None`, **cannot distinguish "no document is
required" from "we never looked"**, falls through to the approve branch, and
commits the insurer to a claim that should have been held for an itemised bill.

### How it was detected — and why the instrumentation missed it

Not by an exception, a cap, or a cost spike. **The broken run is one turn
*longer* and costs *more***, because approving has to pass the gate and
requesting a document stops before it. A cost alarm here would have fired on the
*correct* behaviour.

It was caught by the **code check** in D4, comparing `decision` against the answer
key. That is the honest limit of failure 1's lesson: turns-and-cost
instrumentation is a *cost* instrument, not a *correctness* one, and D7 needs
both because the two failures are invisible to each other's detector.

**Three trials moved, all the same case run three times.** `CLM-8901` is a
negative case, so the 3× trial policy turns one interface defect into three
failed trials. A single trial would have made this a coin-flip finding — the
policy earning its cost. The defect matters out of proportion to its size because
of layer 2: at 8,000 claims/month a wrongly approved claim costs US$7.60 of
assessor time to unwind, and unlike a refusal it has **already committed the
insurer**.

### Which layer the fix belongs in, and why the other two are wrong

- **Tool interface — correct.** The information the decision needs was never
  returned. `check_coverage` already sees the policy and the claim's documents, so
  it is the only place that *can* answer the question. Widening one return is also
  cheaper than a `get_required_documents` tool: a new tool adds a descriptor to
  the prefix, re-billed on every turn whether or not it is ever called (lever 1).
- **Loop control — wrong, and this is the instructive part.** Every guard behaved
  correctly. Nothing repeated, nothing ran long, nothing overspent. **A cap cannot
  detect a fault that makes the run shorter.** Tightening the caps would punish
  the correct runs and leave this one untouched.
- **Prompt — wrong, and the most tempting.** You cannot instruct a model to take
  account of a field the tool never returned. *"Always check whether a document is
  required"* produces a model that **says** it checked. That is the difference
  between a guardrail and a wish, and it is the same reason D3(a) lives in code.

---

## A note on how failure 2 was built, which is itself the D7 lesson

The first version of this reproduction patched only
`tools.REGISTRY["A"]["check_coverage"]` and reported **60/60 → 60/60: no effect**.

The tool is reached by two routes. The loop dispatches through the `REGISTRY`,
which holds the function *object*; the scripted planner calls the module attribute
`tools.tools.check_coverage`. Patching one route left the other live, and the demo
produced a confident null result while looking like it had run.

A reproduction that silently does nothing is worse than one that crashes, for the
same reason failure 1 is worse than an exception: **it is publishable.** Both
routes are now closed and the docstring says why.
