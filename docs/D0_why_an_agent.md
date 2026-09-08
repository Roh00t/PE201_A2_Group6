# D0 · Why an agent at all

**PE6201 A2 · Problem A — health-insurance claim first response**
Owner: Zhao Yujia (drafting) · Rohit Panda (measurements)
Companion to [D0c_what_good_looks_like.md](D0c_what_good_looks_like.md), which was
committed at `c66193f` on 6 September — **before the first agent-code commit**, as
`[brief D0(c)]` requires.

Every number in this document was produced by code in this repository and can be
reproduced with no API key:

```bash
python3 run_eval.py                                   # 60 of 60 trials
python3 experiments/d2c_parallel_vs_sequential.py     # grouping, both ways
python3 experiments/demo_loop_failure.py              # D7 failure 1
python3 experiments/demo_tool_interface_failure.py    # D7 failure 2
```

**Three corrections to the framing this document was commissioned under**, stated up
front because getting them wrong would misrepresent the system:

1. Class 4's ladder has **seven** rungs, not four. Both tables appear in §1: the
   seven-rung ladder we are marked against, and the four architectural families mapped
   onto it.
2. **`request_document` is an outcome, not a tool.** The three outcomes are
   `approve_in_principle` · `request_document` · `escalate`. The seven tools are listed
   in §1.4.
3. **The irreversible step is not a payout.** `issue_decision_letter` writes a *first
   response* — and the brief is explicit that it is *"one log line, not a letter"*. It
   commits the insurer to a stated position communicated to the member. Nothing in this
   system moves money. Claiming otherwise would overstate the risk we designed against,
   and the autonomy argument in §5 is stronger without the exaggeration.

---

## 1 · Placement on the ladder, and what the climb cost

### 1.1 · The ladder we are marked against

Class 4 Capsule 1, from Anthropic's Pre-read 1. Rungs 1–6 are workflows — predictable,
enumerable, testable. **Only rung 7 hands the sequence to the model.**

| Rung | Who decides | Cost | Use it when |
|---|---|---|---|
| 1 · Single call | you | 1 call | one-shot, well-specified task |
| 2 · Prompt chain | you | 2–4 calls | fixed subtasks with a check between |
| 3 · Routing | model picks a lane | 1 + 1 calls | distinct categories |
| 4 · Parallelisation | you | N calls, one wall-clock | independent checks, or a vote |
| 5 · Orchestrator–workers | model, at runtime | unpredictable | the split depends on the input |
| 6 · Evaluator–optimiser | model | unknown rounds | criteria statable; a second pass helps |
| **7 · Agent** | **model** | **unbounded until you cap it** | **steps cannot be known in advance** |

**A2 sits on rung 7. The brief chose the rung; our task is to say what rungs 1–6 would
and would not have delivered, and what rung 7 cost us.** `[brief D0(a)]`

### 1.2 · The four architectural families, and where each breaks

| | Rung(s) | What it delivers on Problem A | Where it breaks, with evidence |
|---|---|---|---|
| **1 · Single prompt** | 1 | Fluent claim summaries. Nothing verifiable. | The model has no access to `policies.json`, so `status`, `end_date`, `annual_limit` and `used_to_date` are **invented**. All **ten** of our negative cases turn on a stored value the model cannot see — policy lapsed, outside policy dates, annual limit exceeded, pre-auth absent, pre-auth expired, required document absent, duplicate of a decided claim, and three shapes of hostile narrative. This is the **monologue** failure the brief names: *"fluent, self-consistent and unfalsifiable."* Fails D0(c) statement 1 (a cause traceable to a record) and statement 4 (say "I don't know") by construction. |
| **2 · Fixed deterministic workflow** | 2–6 | The happy path, cheaply and predictably. A DAG of `get_claim → lookup_policy → check_coverage × N → decide` handles a well-formed 3-line claim. | **The step count is data-dependent, and the data decides it.** `get_preauthorisation` runs only for lines where `check_coverage` returned `requires_preauth: true` — so *N* is not knowable until turn 3 has answered. A DAG must either call it for every line (waste, and a boundary error on unknown codes) or never (D7 failure 2's silent misapproval). Measured evidence in §1.3. |
| **3 · Read-only agentic retrieval** | between 6 and 7 | Everything above, *plus* adaptive re-querying. It could reach the correct decision on all 40 cases. | **It cannot record one.** All six read tools are safe here; the seventh is not. Agentic retrieval is *"simply an agent whose tools are all read-only"* — and *"the governance cliff is not retrieval → agentic retrieval. It is agentic retrieval → agent, at the first write."* |
| **4 · ReAct with a gated write** | **7** | The decision **and** the record, with the write held behind `AUTONOMY = "confirm"`. | Costs unbounded turns until capped, and a per-step reliability that compounds. Both are quantified in §1.5 and §3. |

### 1.3 · The workflow test — answered with our own cases

Four questions separate a workflow from an agent. **The second row is the one that
decides it**, and the brief demands cases from our own evaluation set.

| The question | Workflow | Agent | **Ours** |
|---|---|---|---|
| Who decides the sequence, and when? | in advance, in code | in the moment, by the model | **the model**, at runtime |
| **Does the number of steps vary with the input?** | no | **yes** | **yes — 2 to 5 turns, measured** |
| Can you test every path? | yes | no — outcomes, not paths | **outcomes**; `harness.code_check` compares `decision`, `trigger`, `missing` |
| What does it cost? | predictable: n calls | unpredictable until capped | capped at 8 turns / 60,000 tokens |

**The measured turn distribution, one trial per case, from
`results/scripted/problemA__scripted__v2__2026-09-09.json`:**

| Turns | Cases | Outcomes | Why the run is that length |
|---:|---:|---|---|
| **2** | 4 | 4 × `escalate` | `CLM-8925`, `CLM-8910`, `CLM-8917`, `CLM-8933`. A lapsed policy, a breached annual limit or a duplicate is decidable from **claim-level facts alone**. The run stops before pricing a single line. |
| **3** | 4 | 3 × `escalate`, 1 × `request_document` | `CLM-8901`, `CLM-8941`, `CLM-8952`, `CLM-9035`. On `CLM-8901` coverage answers, a required document is absent, the run stops **before** `get_preauthorisation` and before the gate. |
| **4** | 25 | 23 × `approve`, 2 × `request_document` | No line needs a pre-authorisation, so turn 4 is the gated write. |
| **5** | 7 | 7 × `approve` | `CLM-8842`, `CLM-8861`, `CLM-9003` — at least one line has `requires_preauth: true`, adding a whole turn that **the input decided**. |

**A 2.5× spread in step count across one evaluation set, driven entirely by what the
records say.** `CLM-8925` and `CLM-8842` enter the loop identically — a claim id and
nothing else — and diverge at turn 2 because one policy is lapsed and the other is not.
No fixed workflow can express that without enumerating every branch, and the branch count
is the product of **six independent conditions** — policy validity, annual limit,
duplicate history, per-line exclusion, per-line pre-auth, per-line required document —
times the number of lines on the claim.

This is also the **early-exit** case D4 asks for: pricing lines a claim will never pay is
burned turns, and **8 of 40 cases exit in 2–3 turns** — all of them negatives.

### 1.4 · The two conditions for an agent, both satisfied

An agent is a system where *"the model dynamically directs its own processes and tool
usage."* Two things must hold; remove either and it is something else.

**(a) The steps are not known in advance.** §1.3 measures this.

**(b) It gets ground truth back at every step.** Seven tools, all reading committed
records — `src/tools/tools.py`, `REGISTRY["A"]`:

`get_claim` · `lookup_policy` · `lookup_hospital` · `check_coverage` ·
`get_preauthorisation` · `check_duplicate_claim` · **`issue_decision_letter`** (the only
write, and the only gated call)

The loop in `src/loop_agent.py` appends every observation — including tool **errors** —
to the transcript before the next model call, so reality corrects the model **inside the
run**, not after it. §2 quantifies "at every step."

### 1.5 · What rung 7 cost us

Three costs, each measured rather than asserted.

**(a) Turn inflation, and the quadratic that follows it.** A fixed workflow pays `n`
calls. An agent re-sends the whole transcript every turn: `input ≈ B·T + D·T(T−1)/2`.
Our v2 prefix `B` is **~2,150 tokens**, of which **~1,756 (82%) is tool descriptors** —
re-billed every turn whether a tool is called or not. Measured across 60 trials:

| grouping | turns | calls | input tokens | pass rate |
|---|---:|---:|---:|---|
| sequential | 357 | 360 | 2,322,600 | 60/60 |
| **parallel (ours)** | **211** | 360 | **1,091,400** | **60/60** |

**−41% turns, −53% input tokens, identical call count.** Nothing was removed; the calls
were regrouped. The saving *is* the transcript being re-sent fewer times.

**(b) Unbounded cost until capped.** Rung 7's cost is *"unbounded until you cap it."* Ours
is capped from evidence, not roundness: `MAX_TURNS = 8` is the worst legitimate run (5)
plus three; `MAX_TOKENS_PER_RUN = 60,000` is the worst measured run doubled. **0 of 60
trials reach either.** Under sequential grouping, 11 of 60 breach the ceiling — so the
caps are only defensible *alongside the grouping they were calibrated under*, and we say so.

**(c) The climb is nearly free, and this is the finding that settles it.**

At our measured 18,190 input / 542 output tokens per trial on the cheap tier:

| Layer | Per task | At 8,000 claims/month |
|---|---:|---:|
| Layer 1 — tokens | **US$0.0020** | US$16 |
| Layer 2 — `(1 − P) × US$7.60` at P = 0.80 | **US$1.5200** | US$12,160 |

**Layer 2 is 747× layer 1.** The entire token cost of climbing from rung 1 to rung 7 is
**0.13%** of the cost per task. What dominates is being wrong — US$7.60 of assessor time
per failed claim, from Appendix A.

That is the argument for the climb, and it is not a preference. Rungs 1–3 are cheaper on
layer 1 by an amount too small to see, and worse on layer 2 by an amount that decides the
business case. **An architecture chosen to save layer 1 here is optimising 0.13% of the
bill.**

---

## 2 · Machine-speed grounding — the model against the system of record

### 2.1 · Test 1, the ground-truth test, answered

*"What will tell this loop it is wrong, and how fast?"* Fast and objective → build the
agent, wiring that signal in first.

Six systems of record can contradict the model. Latency is measured over 200 calls each
against the committed fixtures (`data/data_A/`):

| System of record | Rows | Answers | Measured | Contradicts the model about |
|---|---:|---|---:|---|
| `policies.json` | 12 | `lookup_policy` | 1.3 µs | live dates, `annual_limit`, `used_to_date` — **two of three escalation triggers** |
| `procedures.json` + `required_documents.json` | 16 + 6 | `check_coverage` | 3.9 µs | exclusion, `requires_preauth`, `required_document` |
| `preauthorisations.json` | 9 | `get_preauthorisation` | 2.0 µs | whether an approval exists **and is valid on the date of service** |
| `decided_claims.json` | 8 | `check_duplicate_claim` | 1.1 µs | whether this episode was already decided |
| `hospitals.json` | 6 | `lookup_hospital` | 0.6 µs | panel status |
| `claims.json` | 40 | `get_claim` | 0.4 µs | the lines, amounts and documents actually filed |

**An honest limit on those numbers.** These are local JSON fixtures standing in for
production systems. In deployment they are a database query (single-digit ms) or an
internal API (tens to hundreds of ms). **The category is what the test asks about, and the
category survives:** every one answers *synchronously, inside the turn, before the next
model call*. None requires a human, a business day, or a judgement. That is the
"machine speed" the brief means, and it is *"the whole reason a loop is allowed to run
unsupervised."*

**Contrast with what would have failed this test.** Member satisfaction with the decision
answers in days and is a matter of opinion. Had our outcome variable been "was the member
happy", the correct build would have been a workflow with a human gate — the rung below.

### 2.2 · How the contradiction actually lands

The correction is structural, not advisory. Three mechanisms, in order of strength:

**(a) The narrative never becomes a tool argument.** `src/narrative_guard.py` is
**ordinary code outside the loop**, not a tool — deliberately, because a tool the model
chooses to call is a tool it can choose to skip, and hostile text is precisely the input
that argues for skipping. Its three rules fire on **3 of 40 narratives and nothing
else** — every hostile narrative in the set, no false positives:

| Case | Rules hit |
|---|---|
| `CLM-8941` | `imperative_to_the_system`, `imitates_a_tool_result`, `authority_not_in_the_records` |
| `CLM-8952` | `imitates_a_tool_result` |
| `CLM-9035` | `imperative_to_the_system`, `authority_not_in_the_records` |

Its own docstring states the limit plainly: *"a tripwire, not a boundary — the boundary is
that the narrative never reaches a tool argument and can never, by construction, change
what `policies.json` says."*

**(b) Poka-yoke signatures make the illegal call inexpressible.** From
`src/tools/tools.py`:

| Constraint | What it makes **impossible** |
|---|---|
| `check_coverage(code, policy_id, documents_attached=None)` — `policy_id` **required** | Pricing a line against no policy. This costs us one turn per approval (§1.3, the 5-turn cases) and we accept the trade. |
| `procedure_code` validated against `procedures.json` **at the boundary** | A hallucinated procedure code reaching a lookup. Rejected before the read. |
| `date_of_service` parsed as an ISO date before use | A malformed date silently comparing false against `valid_to`. |
| `issue_decision_letter(decision: Literal[...])` + runtime allow-list | A fourth outcome entering the ledger. |
| Totals **re-derived** from the claim record inside the gated write | `approved_total + refused_total` not reconciling against the filed lines. Refused with `sent: false`, **no ledger line written**. |
| Once-only per run (`_DECIDED_THIS_RUN`, cleared by `reset_decision_state()`) | The same claim decided twice in one run — while still allowing the 3 trials a negative case legitimately gets. |

These are **runtime checks, not type hints.** Python annotations do not validate; the
explicit boundary checks do. [D2b_descriptors.md](D2b_descriptors.md) states that distinction rather
than letting the annotations imply enforcement.

**(c) A tool error becomes an observation, not a crash.** `src/loop_agent.py` catches
`KeyError` (hallucinated tool name) and `TypeError` (wrong arguments) and feeds the error
back as the observation. The bad call still enters `evidence`, *"because a trace that hides
the bad call cannot be used to diagnose it."* The model gets one turn to correct itself
from ground truth — which is the ReAct loop doing the exact job it was climbed to for.

---

## 3 · Where a single-agent ReAct loop stops being right

### 3.1 · Test 2, the arithmetic — worked backwards, with our own numbers

Per-step reliability compounds **within one run**. The exponent is the number of steps in
one trajectory, never the number of cases in the evaluation set.

You cannot measure `s` directly. What D4 measures is whether a whole run produced the
right outcome. So work backwards from the measured run pass rate `P` and the measured
median turn count `T`:

```
s = P^(1/T)
```

**`T = 4`, measured.** `P` **is not yet measured and we will not invent it.** The scripted
backend returns 60/60 by construction — it replays moves derived from the records, so
`P = 1.0` would imply `s = 1.0`, which is a statement about our planner, not about any
model. **`P` comes from the D5(b) live battery.** What we can state now is the shape of
the answer across the plausible range:

| Measured `P` | Implied `s` | Same `s` at T=2 | T=3 | **T=4** | T=6 | T=8 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.70 | 0.9147 | 0.84 | 0.77 | **0.70** | 0.59 | 0.49 |
| 0.80 | 0.9457 | 0.89 | 0.85 | **0.80** | 0.72 | 0.64 |
| 0.90 | 0.9740 | 0.95 | 0.92 | **0.90** | 0.85 | 0.81 |

**The whole argument in one row.** At `P = 0.80` the implied per-step reliability is
0.9457 — and *the same agent, at the same per-step quality*, scores anywhere from **0.89
to 0.64** on turn count alone.

**We can already price the turn-count lever, because we measured both groupings.**
Sequential grouping ran 357 turns over 60 trials — **5.95 turns per run** against our
4.0. Holding `s = 0.9457` fixed:

```
T = 4.00 (parallel)     P = 0.800
T = 5.95 (sequential)   P = 0.718      −8.2 percentage points
```

And that pass rate is exactly what sets layer 2:

| | P | Layer 2/task | Monthly at 8,000 |
|---|---:|---:|---:|
| parallel | 0.800 | US$1.52 | US$12,176 |
| sequential | 0.718 | US$2.14 | US$17,162 |

**US$4,986 per month from grouping alone**, at identical per-step quality and an identical
call count. D0's arithmetic, D2(c)'s grouping and D6's layer 2 are **one argument measured
three times**, and this is the number that joins them.

**The limits, stated because they are real.** Steps are **not independent** — a bad
observation early makes later steps worse, not equally likely to succeed. And not every
step is equally failure-prone: the turn that reads a policy row is near-perfect (it is a
dictionary lookup); the turn that judges a member's free-text narrative is not. A single
`s` averages them and hides which is which. **Treat `s` as a diagnostic, not a constant:**
it answers *"is our problem step quality, or step count?"*

**Which our evidence points at, so far.** Step **count** — because it is the only one we
have moved and measured (−41% turns for zero correctness cost). Step **quality** is
unmeasured until the battery runs, and the method is already specified: group failing
trials by the tool call immediately preceding the failure. Our prior is that
`check_coverage` on a hostile narrative is the weak step, because it is the only turn
whose input is written by someone outside the organisation. **We will report what the
grouping shows, not the prior.**

### 3.2 · Where the architecture breaks — evidence from our two deletions

[D7_failures.md](D7_failures.md) builds both as deletions from the working agent, not as separately
written bad agents.

**Loop control.** Delete `Guardrails.check_duplicate` and the agent repeats a call it
already made: **5 → 7 turns, 29,520 → 48,960 tokens, 1.66× cost — and the same correct
answer.** Nothing raised. Nothing capped. A pass-rate table scores it as a clean pass.
This is the rung-7 tax made concrete: at rung 4 the call count is fixed by you and this
failure cannot occur.

**Tool interface.** Narrow `check_coverage` back to its pre-widening return and the set
drops **60/60 → 57/60**, with `CLM-8901` flipping from `request_document` to a silent
`approve_in_principle` — an insurer committed to a claim that needed a document. The
broken run is **one turn longer and costs more**, so a cost alarm would have fired on the
*correct* behaviour.

**Together they bound what instrumentation can see.** Turns-and-cost is a *cost*
instrument. Outcome grading against the answer key is a *correctness* instrument. **Each
failure is invisible to the other's detector**, which is why D4 grades outcomes and D7
requires two failures in different layers.

### 3.3 · The architecture we did not build

**Multi-agent** — a triage agent, a coverage agent, a decision agent, an orchestrator. We
stayed single-agent, and the reasons are costs we can quantify:

| | Cost of the multi-agent version | Our evidence |
|---|---|---|
| **Token tax** | Each sub-agent carries its own prefix. Our `B` is ~2,150 tokens, ~1,756 of it descriptors. Four agents means four prefixes plus a hand-off transcript between them — and `B·T` is linear in turns for *each*. | §1.5(a) |
| **Turn inflation** | The lever that moved `P` by 8.2pp is **turn count**. Orchestration adds turns for coordination that answer no question about the claim. Multi-agent makes the biggest measured lever worse. | §3.1 |
| **Auditability** | Our ledger row carries one ordered `evidence` list. Across four agents the trail forks, and D0(c) statement 1 — *a cause traceable to a record* — becomes a join across four transcripts. | §5.3 |
| **The write does not decompose** | There is exactly **one** irreversible action. Splitting the readers around a single writer buys no isolation; it adds hand-offs in front of the same gate. | §5.1 |

**The counter-argument, stated fairly, and the evidence for it.** Multi-agent would give
each sub-agent a shorter prompt and a narrower job — plausibly raising `s` on the weak
step. Pre-read 5 records **Cognition's own reversal** on exactly this, and the finding
that in their working version **the writes stay single-threaded**. Our decomposition would
have put the writes on one path anyway; we skipped the orchestration and kept the property.

**Where we would change our minds.** If the battery shows `s` concentrated in one step
rather than spread, a specialist sub-agent for that step becomes arguable. If it is spread,
multi-agent buys prefix cost and hand-off turns for nothing. **We are not claiming
single-agent is right in general — we are claiming it is right at seven tools, one write
and a median of four turns**, and naming the measurement that would overturn it.

---

## 4 · Evaluation cases and guardrail cases are different instruments

### 4.1 · The distinction

| | Evaluation case (D4) | Guardrail case (D3b) |
|---|---|---|
| **The question** | *Did it get the job right?* | *Did it refuse, cap, or escalate?* |
| **Set** | **40 cases · 10 negative · 60 trials** | **15 cases** — 13 `must_fire`, 1 `must_not_fire`, 1 `known_limit` |
| **Graded against** | `data/expected_outcomes_A.json` — `decision`, `trigger`, `missing` | Observed runtime behaviour — `stopped_by`, `ledger_lines_written`, `approve_calls` |
| **Passing means** | the outcome matched the answer key | the **code** stopped the agent |
| **What it exercises** | the model's judgement | `src/backends/guardrails.py` — which contains **no model** |
| **Trials** | ordinary ×1, negative ×3 | ×1, plus `--twice` for determinism |

**A negative evaluation case is still an evaluation case.** Its correct outcome is `ask`
or `escalate` — anything except the act — and it asks whether the agent *reached the right
outcome*. `CLM-8925` (lapsed policy → `escalate`) is a negative eval case: escalating is
the **right answer**, not a refusal.

The brief names the failure mode directly: *"a team that files all its hostile-input tests
as evaluation cases has a 40-case eval set and an empty guardrail checklist."* We hold both.
`CLM-8952` (hostile narrative → `escalate`) is an **eval** case, because there is a correct
outcome to reach. `GR-11` (`hostile_imperative`) is a **guardrail** case, because it asks
whether the code fires when the agent *attempts* the bad action.

### 4.2 · Why 100% on one says nothing about the other

**Both directions are real, and we have measured one of them.**

**Perfect evaluation, dangerous agent.** Our agent scores **60/60**. Delete
`Guardrails.check_duplicate` and it *still* scores 60/60 while burning 1.66× the tokens
(§3.2). The evaluation set cannot see it — outcome grading asks what was concluded, and
the conclusion was correct. **The guardrail set exists because a correct answer at any cost
is not a safe system.** `GR-04` (`duplicate_action`) catches in one deterministic case what
60 evaluation trials cannot see at all.

**Perfect guardrails, useless agent.** An agent that escalates everything passes every
`must_fire` case — it never attempts a bad action. It fails 30 of 40 evaluation cases. That
is why `GR-14` is a `must_not_fire` control: a guardrail suite without one measures only
how loudly you can say no.

### 4.3 · The limit we state rather than hide

**A scripted guardrail run proves the guardrail fires when the agent *attempts* the bad
action. It cannot tell us whether a live model can be talked into attempting it.** That is
a D5(b) observation, not a guardrail result. `[upd]`

`GR-15` is committed as a **documented `known_limit`**: the keyword-and-shape detector
misses a semantic paraphrase. It is excluded from the pass denominator and reported
separately — 13/13 `must_fire` **plus one recorded miss**, never 14/14. We do not claim
prompt-injection resistance; we claim a tripwire in front of a structural boundary.

---

## 5 · The autonomy setting, chosen against the irreversible step

### 5.1 · Naming the irreversible action

**`issue_decision_letter` — `tools.GATED_ACTION["A"]`.** The only tool in the set that
writes. The other six are read-only lookups that can be re-run harmlessly all day.

**This write is the entire reason we are on rung 7 rather than 5 or 6.** *"The governance
cliff is not retrieval → agentic retrieval. It is agentic retrieval → agent, at the first
write."* Remove `issue_decision_letter` and this system is agentic retrieval, needing no
autonomy setting at all.

**What is irreversible about it, precisely.** Not money — nothing here moves money. The
insurer is now **on record** with a first response communicated to the member: a stated
approved total, a stated exclusion rule, or a named missing document. A wrong `escalate`
costs a queue position. A wrong `approve_in_principle` costs a position the insurer has
to walk back, plus **US$7.60** of assessor time to unwind (Appendix A), against 8,000
claims a month.

### 5.2 · Why `confirm`, argued against the risk and not by taste

`AUTONOMY = "confirm"` — `src/config.py:110`.

| Setting | What it does | Why not |
|---|---|---|
| `act` | writes without asking | The write is irreversible and the failure is asymmetric. D7 failure 2 produced a **silent wrong approval that no guardrail could detect** — 60/60 → 57/60, one turn *longer*, costing *more*. Under `act` that reaches the member. |
| `suggest` | never writes | Fails D0(c) statement 5 — *costs less than a person*. If a human writes every letter, layer 2 is 100% and the agent has moved work, not removed it. It also makes the eval set unmeasurable: 30 of 40 cases have `approve_in_principle` as the correct outcome. |
| **`confirm`** | **holds the gated call for approval; everything before it runs unsupervised** | **The gate sits in front of the ACTION, not in front of the agent.** |

That last distinction carries the argument. *"An agent gated as a whole is not an agent,
it is a form."* All six read tools run without asking, in parallel where the dependency
rule allows, across a median of four turns. **Exactly one call stops.** The autonomy
setting is placed against the irreversible step, which is what the rubric asks for.

**The evidence that the placement is right.** `CLM-8925` escalates at **two turns without
ever reaching the gate**; `CLM-8901` requests a document at **three**. **10 of 40 cases
never reach the gated action at all** — the 7 escalations and the 3 document requests.
A whole-agent gate would
have made a human approve 40 runs to obtain 30 letters; the 10 negatives need no approval
because they never write, and the ledger records that by their absence.

### 5.3 · What the gate records, and why the record is the deliverable

The rubric is explicit: *"the gated action logs a decision with its evidence trail and its
gate — effort spent on documents, interfaces or integrations earns nothing here."*

The loop deposits what only it knows (`tools.set_run_context()`) **immediately after the
gate passes** — so a *held* gate writes nothing — and the row is written in one place,
**inside the gated action itself**. That placement is deliberate: a blocked call must leave
no ledger line, and the only way to guarantee that is for the writer to be the thing doing
the blocking.

One real row from `logs/decisions.jsonl`, abridged:

```json
{ "ts": "2026-09-09T00:36:21", "case_id": "CLM-8842",
  "decision": "approve_in_principle",
  "reason": "A disposition for every line, then send. This is the irreversible
             step, so it goes through the gate - and it is a turn like any other.",
  "evidence": ["get_claim", "lookup_policy", "lookup_hospital",
               "check_coverage", "check_coverage", "check_coverage",
               "get_preauthorisation"],
  "gate": { "name": "issue_decision_letter", "autonomy": "confirm", "approved": true },
  "turns": 5, "tokens_in": 21000, "tokens_out": 600,
  "cost_usd": 0.00234, "lines_resolved": 3,
  "approved_total": 2180, "refused_total": 300, "backend": "scripted" }
```

| Field | Answers | Serves |
|---|---|---|
| `reason` | why — **in the agent's own words at the moment it committed**, not the tidied version written afterwards. If the two disagree, this is what it believed. | D0(c) 1 |
| `evidence` | which records were consulted, **in order**. A decision whose trail lacks `check_coverage` is a decision nobody checked coverage for, readable straight off the row. | D0(c) 1, 2 |
| `gate` | which gate, which autonomy, who passed it | D3(a) |
| `turns`, `tokens_*`, `cost_usd` | what it cost | D6 layer 1, D7 |
| `approved_total` / `refused_total` | **re-derived** inside the write; refuses on a mismatch | D0(c) 3 |

**It is one log line, not a letter.** No prose, no template — the brief is explicit that
*"nothing in Rubric 1 marks the wording of that string."*

**The ledger is append-only, so the committed artifact is one clean pass:** 30 rows, one
per approved claim, from `rm -f logs/decisions.jsonl && python3 run_eval.py`. **30, not
40** — because 10 cases correctly never reach the gate, and the ledger says so by their
absence.

---

## 6 · What this document commits us to

| Claim | Status | Where it is settled |
|---|---|---|
| Step count varies with the input | **Measured** — 2 to 5 turns, 40 cases | §1.3 |
| Ground truth arrives at machine speed | **Measured** — six SoRs, synchronous, with the fixture caveat stated | §2.1 |
| Grouping is the dominant lever | **Measured** — −41% turns, −53% tokens, −8.2pp implied `P` | §1.5, §3.1 |
| Layer 2 dominates layer 1 by 747× | **Measured** on our tokens, at Appendix A's US$7.60 | §1.5(c) |
| Guardrails catch what evaluation cannot | **Measured** — 1.66× cost at an unchanged 60/60 | §3.2, §4.2 |
| The gate is in front of the action | **Shipped** — 12 of 40 cases never reach it | §5.2 |
| Implied per-step reliability `s` | **Pending D5(b).** `T = 4` is measured; `P` is not, and we have not invented it | §3.1 |
| Which lever to pull — step quality or step count | **Pending.** Method specified: group failing trials by the preceding tool call | §3.1 |

The last two rows are the honest state of this document on 9 September. **`P` is the one
number D0's arithmetic needs and the live battery has not yet run.** Everything else here
is reproducible today, without a key, from a clean clone.

---

### Sources

`[brief]` `PE6201_A2_Applied_AI_System.pdf` — D0(a) ladder and the seven rungs; D0(b)
both Capsule 1 tests; the three-question test and the governance cliff; Appendix A's
routing table, volume (8,000/month) and failure cost (US$38/h × 12 min = US$7.60).
`[faq]` `PE6201_A2_FAQ.pdf` — evaluation vs guardrail cases; the exponent is steps in one
run. `[upd]` `PE6201_A2_Document_Updates.pdf` — the scripted-guardrail caveat.
`[lect]` `docs/slides_notes.md` — Class 4 slide 9, the seven-rung taxonomy; `B·T + D·T(T−1)/2`.
Pre-read 1 (Anthropic, *Building effective agents*) · Pre-read 5 (Cognition's reversal on
multi-agent, and single-threaded writes).
