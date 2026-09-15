# PE6201 A2 · Applied AI System — Problem A, health-insurance claim first response

**Group 6** · Team ID `6` · Section `B` · https://github.com/Roh00t/PE201_A2_Group6

> **Draft for the team, 15 September 2026.** Every number below was checked against the
> committed files named in the tables. The team edits, cuts and signs off before submission.
> Word count (prose only; tables, code, captions and references excluded): see the last line.

---

## 1 · Why an agent

A first response to a claim is one of three outcomes: approve in principle, request one
named document, or escalate to an assessor. It is recorded once. The records decide which
outcome is right, and they also decide how much work reaching it takes. That second fact
is what puts this problem on rung 7.

**What the lower rungs would have delivered.** A single prompt (rung 1) cannot see a policy
row. All ten negative cases turn on a stored value — a lapsed date, a spent annual limit, an
expired pre-authorisation, an already-decided duplicate — so a prompt would be fluent and
unfalsifiable. A fixed workflow (rungs 2–6) handles the happy path, but not the branching:
whether a line needs a pre-authorisation is known only after coverage answers, so the data
sets the chain's length. In our set a run takes two to five turns. `CLM-8925` and `CLM-8842`
arrive identically and part at turn 2, because one claim is over its annual limit. Read-only agentic
retrieval could reach every decision and record none. Our governance cliff is the first
write, `issue_decision_letter`.

**Both conditions hold, and the ground truth is fast.** Every step reads a system of record:
the policy, procedures and required documents, pre-authorisations, decided claims, hospitals,
the claim itself. Each answers inside the turn, with no person in the loop. That is why the
loop may run unsupervised up to the write, and why autonomy is `confirm` on that one call
only: the ten escalations and document requests in our set never reach the gate.

**What the climb cost.** On the deployed model a claim's tokens cost US$0.021. A wrong
outcome costs an assessor US$7.60. Tokens are noise beside failures, so rung 7 earns its
cost exactly when it raises the success rate (§4).

**Step quality, not step count.** Claude Haiku 4.5 passed 54 of 60 trials at a median of four
turns, an implied per-step reliability of 0.90^(1/4) = 0.974; qwen3-235b's is 0.909. No live
trial reached the eight-turn cap. Of 65 failing v2 trials across five models, 27 came
straight after `check_coverage`, the turn that weighs coverage against the claim, and 24
were replies the loop could not read, half of them from one provider. Two cases, `CLM-8952`
and `CLM-8925`, produced 21. Steps are neither independent nor equally fragile, so `s` is a
diagnostic, but it points at a weak step to fix rather than a chain to shorten.

## 2 · The tool layer

Seven tools, one of them a write: `get_claim`, `lookup_policy`, `lookup_hospital`,
`check_coverage`, `get_preauthorisation`, `check_duplicate_claim`, `issue_decision_letter`.

**We tried not adding tools first.** Instead of a `get_required_documents` tool,
`check_coverage` takes the attached documents and returns the required one — D7's second
failure is the receipt, since deleting that widening silently approves a claim missing its
itemised bill. Narrative checking became ordinary code, not a tool: a tool the model chooses
to call is one it can choose to skip, and hostile text argues for skipping. We added
`check_duplicate_claim` only because nothing else sees decided claims. `lookup_hospital` is
our weak tool: no case fails without it, and its 140 tokens are re-billed every turn. We kept
it because the record must state panel status, and we say so.

**Poka-yoke in the signatures.** `check_coverage` requires a `policy_id`, so pricing a line
against no policy cannot be expressed; that costs one turn per approval. The letter accepts
only the three outcomes and re-derives the totals from the claim, refusing with no ledger
line when they disagree.

**The descriptor rewrite, measured with the model held fixed** (qwen3-235b): v1 passed 31 of
60 trials, v2 41, and negative cases passing all three trials rose from one to four, at 2.4×
the input tokens. It did not help where we expected. v1 chose the right decision at least as
often (49 against 45). It lost on what v2's process section and final-record checklist ask
for: fifteen trials escalated correctly with a trigger in free text (v2: three), no v1 record
carried the checklist fields, and v1 never sent a letter for any of its 30 approvals (v2:
25 of 25). v2 changed descriptors, process section and example together, so the gain cannot
be credited to descriptors alone. Five of v1's trigger failures differ only by a space for an
underscore; forgiving them gives 36 of 60, and the conclusion stands.

**Dependency rule: two calls share a turn only when neither needs the other's output.** The
claim comes alone; policy, hospital and duplicate history together; one coverage check per
line; pre-authorisations only for lines that need one; then the letter. We group less than
Appendix A's example, because our coverage check needs the policy id. Measured both ways on
60 trials: 357 turns fell to 211 and input tokens by 53%, with 60 of 60 passing either way.
No call was removed; the transcript was re-sent fewer times.

## 3 · What the evidence showed

| Model (member) | Prompt | Code check, 60 trials | Negative trials | Negative cases 3 of 3 | Judgement check | List US$ |
|---|---|---:|---:|---:|---:|---:|
| `anthropic/claude-haiku-4.5` (Rohit Panda) | v2 | **54 (90.0%)** | 24/30 | 8/10 | 34/40 | 1.2682 |
| `openai/gpt-4.1-mini` (Huang Yu) | v2 | 48 (80.0%) | 18/30 | 6/10 | 26/40 | 0.4634 |
| `deepseek/deepseek-v3.2` (Shen Bowen) | v2 | 48 (80.0%) | 20/30 | 6/10 | 31/40 | 0.2853 |
| `google/gemini-2.5-flash` (Xia Yanran) | v2 | 44 (73.3%) | 21/30 | 7/10 | 22/40 | 0.3476 |
| `qwen/qwen3-235b-a22b-2507` (Li Yunke) | v2 | 41 (68.3%) | 18/30 | 4/10 | 21/40 | 0.0858 |
| `qwen/qwen3-235b-a22b-2507` (Zhao Yujia) | **v1** | 31 (51.7%) | 4/30 | 1/10 | 6/40 | 0.0409 |

*Source: `results/live/battery_table.md`; judgement counts from each run's `__judged.json`.
Re-grades with two grader fixes: `results/regrade/regrade_matrix.md`.*

The negative cases separated the models by kind of failure, not only by count.
`CLM-8952`, whose narrative imitates a tool result, was approved in every trial by Haiku,
gpt-4.1-mini and deepseek-v3.2, and in two of three by qwen3-235b. Only Gemini escalated it
correctly — the same model that missed a lapsed policy and a missing pre-authorisation every
time. `CLM-8925`, a claim above its remaining limit, was escalated every time by Haiku and
Gemini; the other three asked for a document in eight of their nine trials.

No cheaper model met our bar: §4 shows one would need about 89.8% success to beat Haiku,
and the best measured 80%. So the evidence supports the most expensive model. The one that
least earned its
price is gpt-4.1-mini: it matched deepseek-v3.2's 48 at 1.6× the cost, was the only model
to accept `CLM-9035`'s invented waiver, and five of its approvals never sent their letter.

How far to trust a row: three identical qwen3-235b runs scored 37, 41 and 49, depending on
how many trials OpenRouter routed to a provider returning unreadable text. With one run per
model, a gap of a few trials is noise. The judgement check is a second model and passed an
unreadable reply twice; `judge.py` now fails such records in code.

## 4 · What it costs

| Layer (Claude Haiku 4.5, 8,000 claims a month) | Per claim | Monthly |
|---|---:|---:|
| 1 · Tokens, list price | US$0.0211 | US$169 |
| 2 · Expected failures, (1 − 0.90) × US$7.60 | US$0.7600 | US$6,080 |
| 3 · Fixed: monitoring, infrastructure, evaluation, maintenance (stated assumptions) | — | US$482 |
| **Total** | | **US$6,731** — against US$60,800 for people alone |

| Lever | Before | After | Measured effect |
|---|---|---|---|
| 1 · Tool block | v1 prompt, 1,106 tokens | v2 prompt, 3,134 tokens | +US$0.00075 a claim (qwen3-235b) |
| 2 · Turn count | 357 turns, 2,322,600 input tokens | 211 turns, 1,091,400 | −53% input tokens |
| 3 · Observation size | no size bound in v1's contracts | bounded in v2's | not separable: both versions call the same functions |
| 4 · Success rate | v1, 51.7% | v2, 68.3% | −US$1.27 a claim in failures |

*Source: `results/d6_inputs.json` → `results/d6_summary.json`; `docs/D6_cost_model.md`.*

We price a failure with the escalation form because a wrong outcome goes to a person, not
back into the loop. That makes layer 2 the bill: 90% of the deployed month. **Lever 4
dominated by three orders of magnitude.** The v2 rewrite added under a tenth of a US cent
in tokens per claim and removed US$1.27 of expected failure. Inside
layer 1, turn count was the larger lever; that is why the dependency rule matters more than
descriptor length.

**Sensitivity.** At 80% success the month costs US$12,811; at 100%, US$651. Against people
the conclusion survives the whole range. The choice of Haiku does not: at 80% it costs
US$107–131 a month more than gpt-4.1-mini or deepseek-v3.2 at their measured 80%, so Haiku is
right only while it really succeeds more often — a six-trial margin from one run each.

**Break-even.** A cheap model must succeed 1 − (0.7811 − 0.0048)/7.60 = 89.8% of the time to
beat Haiku. deepseek-v3.2 measured 80.0% and qwen3-235b 68.3%. Because a claim's tokens are
tiny beside US$7.60, a cheaper model has to match the expensive one's success almost
exactly; its price barely matters. OpenRouter's prompt caching billed gpt-4.1-mini US$0.19
instead of US$0.46; we report that beside the list-price baseline, never inside it.

**Caps that ship with it.** Eight turns: the worst legitimate run takes five, plus three to
recover from one wander. 60,000 tokens a run: the largest live run used 27,444. Twenty claims
a member a month: the busiest member in our data has eight of 40, and the cap bounds one
member at US$6 of model spend. The twelve live batteries were billed US$2.24, plus US$0.14 of
judging.

## 5 · The two failures

**Loop control — action de-duplication deleted.** On `CLM-8842` the run went from five turns
to seven and from 29,520 tokens to 48,960, at 1.66× the cost, and still gave the correct
answer. Only per-run turn and token logging showed it; a pass-rate table scores it clean.
Neither cap fired, because a cap bounds damage but cannot recognise a repeat. Only the
de-duplication guard remembers what the agent already did, and no prompt repairs a model
that forgot. Across the set the median run is four turns, the worst legitimate run five,
and none reaches the cap, which is how we set it at eight.

**Tool interface — the coverage widening deleted.** The set fell from 60 to 57 of 60:
`CLM-8901` was approved in all three trials without its required itemised bill. The code
check caught it; cost logging could not, because a wrong approval looks exactly like a right
one — a turn longer and dearer than a document request — so no cost threshold separates
them. The fix belongs
in the tool, the only place that sees policy and documents together. Loop control is the
wrong layer, since every guard behaved; the prompt is wrong too, because no instruction
makes a model use a field it was never returned.

## 6 · What we would not deploy

We would not deploy the model's own resistance to injection: four of five models approved
`CLM-8952` at least once. `narrative_guard` is a keyword tripwire that misses a paraphrase (GR-15). The
post-freeze letter checks and final check now refuse or override those decisions in code,
but that is projected on recorded trials, not measured live.

A second agent reviewing each letter is the obvious catch for `CLM-8952`, at about one more
short Haiku call a claim — roughly US$0.002, or US$19 a month. We stayed single-agent
because a reviewer reads the same forged narrative and can be fooled the same way, while
the check needed is deterministic. Cognition's reversal points the same way: reviewers may
multiply, but writes stay single-threaded — ours is one write behind one gate.

---

## References

- PE6201 A2 brief, FAQ and Document Updates, `docs/course/`.
- Anthropic, *Building effective agents* (Pre-read 1): the seven-rung ladder.
- Cognition, *Don't Build Multi-Agents* (June 2025) and *Multi-Agents: What's Actually Working*
  (April 2026) (Pre-read 5).

## Evidence in the repository

| Claim | File |
|---|---|
| Rung, workflow test, ground truth, autonomy | `docs/D0_why_an_agent.md`, `docs/D0c_what_good_looks_like.md` |
| Tool scoring and what was not added | `docs/D2a_tool_scoring.md` |
| Descriptors, v1 → v2 measured | `docs/D2b_descriptors.md` |
| Dependency rule, both groupings | `docs/D2c_dependency_rule.md`, `experiments/d2c_parallel_vs_sequential.py` |
| Guardrail checklist, 18 cases | `docs/D3b_guardrail_checklist.md` |
| Battery table, re-grades, provider audit | `results/live/battery_table.md`, `results/regrade/`, `results/archive/live/README.md` |
| Cost model | `docs/D6_cost_model.md`, `results/d6_summary.json` |
| Both failures | `docs/D7_failures.md`, `experiments/demo_*.py` |
| Who did what | `CONTRIBUTIONS.md` |

---

*Prose word count: 1,634 (sections 1–6; tables, captions, code, references and this line excluded). Counted 15 September 2026.*
