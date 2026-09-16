# A2 Team Self-Appraisal

**PE6201 Emerging AI Technologies · Assessment 2 of 2 · Required cover sheet**

| | |
|---|---|
| **Team ID** | `B-6` — *confirm before submitting; see note 1* |
| **Section** | `B` |
| **Problem chosen (A / B)** | **A** — health-insurance claim first response |
| **Members** | Rohit Panda · Huang Yu (黄煜) · Li Yunke · Shen Bowen · Xia Yanran · Zhao Yujia |
| **Repository URL** | https://github.com/Roh00t/PE201_A2_Group6 |
| **Date** | `____________` |

> **Note 1 — Team ID.** The course issues identifiers in the form `B-4`. Our report currently
> reads "Team ID 6 · Section B", and `CLAUDE.md` and `CONTRIBUTIONS.md` still read `<FILL>`.
> `B-6` is our reading of that. Confirm it, then set it identically in all four places and in
> the archive name `PE6201_A2_B-6.zip`.
>
> **Note 2 — Dates.** The sheet template we hold states 13 September, and peer rating closing
> 16 September. Per the course update those are now **Sunday 20 September** and
> **Thursday 24 September 2026**. This sheet is filed against the updated dates.

---

## 1 · Rate your team against Rubric 1

| Criterion | Weight | Excellent (4) | Proficient (3) | Developing (2) | Limited (1) |
|---|---|:---:|:---:|:---:|:---:|
| Conceptual Understanding | 25% | **✗** | | | |
| Technical Execution | 30% | **✗** | | | |
| Reasoning & Justification | 25% | **✗** | | | |
| Communication & Clarity | 20% | | **✗** | | |

**Why we did not mark ourselves Excellent everywhere.** Three of our four ratings rest on
things a marker can re-run rather than take on trust: the scripted harness reproduces from a
clean clone with no key (60/60 trials), both D7 failures are deletions from the working agent
that name the wrong layers as well as the right one, and our D2(b) rewrite is reported
against us — v1 chose the right decision more often than v2 (49 against 45), and we say so.

We rate **Communication & Clarity as Proficient, not Excellent**, and the gap is deliberate.
Our report argues rather than narrates and sits inside the word cap, but the repository is
not yet as navigable as the code is good: `CONTRIBUTIONS.md` carried stale commit counts and
an unfilled authorship table until late, `CLAUDE.md` describes a directory layout that does
not match the tree, and the repository still holds working notes that are not deliverables.
A reader who was not in our team meets those before they meet the harness.

---

## 2 · The one decision you would defend hardest

**Putting the hostile-narrative check in ordinary code rather than in a tool, and gating the
decision letter on it.** A tool the model chooses to call is a tool it can choose to skip, and
a narrative written to manipulate the system argues precisely for skipping it — so a
`check_narrative` tool would be absent exactly when it mattered. The evidence came from our
own battery: on `CLM-8952`, whose narrative imitates a tool result, four of our five models
approved the claim at least once, and one `gpt-4.1-mini` trial approved it without ever
calling `check_coverage`, acting on a "check_coverage returned…" line the member had typed.
Only Gemini escalated it correctly, and that same model missed a lapsed policy and an absent
pre-authorisation every time — so no model in our price range could be trusted to resist this
on its own. `issue_decision_letter` now refuses to write any letter on a flagged narrative,
whatever decision the model reached and whatever its arithmetic says, and the refusal leaves
no ledger line. We state the limit plainly: it is a keyword-and-shape tripwire that misses a
semantic paraphrase, recorded as guardrail case GR-15 and excluded from our pass denominator
rather than hidden inside it.

---

## 3 · The one you are least sure about

**Whether our step cap of 8 turns is calibrated to the right thing.** We derived it honestly —
the worst legitimate run in our scripted distribution is 5 turns, plus three turns of margin
for a live model that wanders once and recovers — but the distribution it came from is
produced by a deterministic planner that never wanders, never re-reads and never mis-parses.
It is a lower bound on turn count, not a sample of live behaviour. Our live battery then
showed no trial reaching the cap, which is reassuring but is not the same as validating it.

The related uncertainty is that our caps are calibrated to the *parallel* grouping and we say
so: run the same work one call per turn and 11 of 60 trials breach a ceiling and halt, not
because any answer was wrong but because the run got long. A cap is only defensible alongside
the grouping it was derived under, and we have measured that dependency rather than resolved
it.

We are also aware that our post-freeze letter checks and final check are **projected on
recorded trials, not measured live** — we did not have the budget to re-run six batteries
after merging them, and we would rather say that than imply a measurement we did not make.

---

## 4 · Your headline numbers

| | Value | Source |
|---|---|---|
| Evaluation cases | **40** (30 ordinary · 10 negative) | `data/expected_outcomes_A.json` |
| Guardrail cases | **18** — 16 must-fire, 1 must-not-fire, 1 documented known limit | `evals/guardrail_cases.json` |
| Negative cases | **10** | derived by `battery_provenance.plan_shape()` |
| Live runs per model (D4) | **60 trials** (30 × 1 + 10 × 3) | derived, never typed |
| Pass rate (best model) | **90.0%** — 54/60, `anthropic/claude-haiku-4.5`, v2 | `results/live/battery_table.md` |
| Pass rate on negatives only | **80.0%** — 24/30 negative trials; 8/10 cases passed 3-of-3 | `results/live/battery_table.md` |
| Models in the battery | **5 distinct models across 5 families**, 6 battery rows (the sixth is the v1 pass, model held fixed) | `evals/battery_roster.json` |
| Median turns per run | **4.0** (live, Haiku 4.5; scripted median also 4.0, worst legitimate 5) | battery summary |
| The live model **I** ran (D5b) | **`anthropic/claude-haiku-4.5`** — Rohit Panda, mid tier | run `d05a3189ca96` |
| My pass rate on it | **90.0%** — 54/60 trials, v2 prompt, 13 Sep 2026 | `results/live/battery__rohit_panda__…json` |
| Turns saved by parallel calls | **357 → 211 turns (−41%)**; input tokens 2,322,600 → 1,091,400 (**−53%**); 360 calls either way, 60/60 passing both | `experiments/d2c_parallel_vs_sequential.py` |
| Cost per successful task | **US$0.7811** — layer 1 US$0.0211 + layer 2 US$0.7600 | `results/d6_summary.json` |
| Monthly cost at problem volume | **US$6,731** at 8,000 claims/month, against US$60,800 for people alone | `results/d6_summary.json` |
| Break-even success rate | **89.8%** — the rate a cheap model needs to beat Haiku; `deepseek-v3.2` measured 80.0%, so none of ours clears it | `results/d6_summary.json` |
| Tokens per call — v1 → v2 | **1,240 → 3,134 tokens** of system prompt, re-billed on every turn (+2.1× cost per trial) | `docs/D2b_descriptors.md` |
| Pass rate — v1 → v2, same model | **51.7% → 68.3%** on `qwen/qwen3-235b-a22b-2507`, model held fixed (+16.7pp); negative 3-of-3 **10% → 40%** | `results/live/battery_table.md` |

**On the last two rows.** The rewrite was measured with the model held fixed, as D2(b)
requires, and it helped — but not where we expected. v1 chose the right decision at least as
often as v2 (49/60 against 45/60); what it never did was write a trigger from the fixed set,
fill the final-record checklist, or send a decision letter for any of its 30 approvals (v2:
25 of 25). Because v2 changed the descriptors, the process section and the worked example
together, the gain cannot be credited to the descriptors alone, and we do not claim it.

**On the caps that ship with the cost model:** step cap 8 turns · budget ceiling 60,000 tokens
per run · 20 claims per member per month. Our twelve live batteries were billed **US$2.24**
in total, plus **US$0.14** of judging — inside the US$3 per-member ceiling for every member.

---

## 5 · Contribution

Matches `CONTRIBUTIONS.md` §§1–2 and the commit history on `main`.

| Member | Owned | Also contributed to |
|---|---|---|
| **Rohit Panda** | D1 the ReAct loop, multi-call turns and per-run instrumentation · D2(a) tool scoring · D2(c) dependency rule · D5(a) scripted backend and planner · D5(b) battery infrastructure, provenance fingerprint and checkpointing | D0(c) *what good looks like* · both D7 reproductions · the gated-action ledger and its seven pre-write checks · `narrative_guard` · README, CLAUDE.md, GUARDRAILS.md · live model `anthropic/claude-haiku-4.5` |
| **Huang Yu (黄煜)** | D2(b) six-field descriptors and the v1→v2 rewrite · D3(a) guardrail code layer · D3(b) guardrail checklist | runtime boundary validation (procedure codes, ISO dates, totals, decision allow-list) · `prompt.descriptor_set()`, without which `PROMPT_VERSION` selected nothing · live model `openai/gpt-4.1-mini` |
| **Li Yunke** | D4 evaluation harness · code check and judgement check graders · the committed judge prompt and its offline rehearsal suite · answer-key joins | independent reproduction of the scripted run · live model `qwen/qwen3-235b-a22b-2507` |
| **Shen Bowen** | D6 cost ledger, ±10pp sensitivity and break-even · OpenRouter price verification | the checkpoint fix that stops a resumed battery re-charging a completed canary · report §§4–5 · live model `deepseek/deepseek-v3.2` |
| **Xia Yanran** | Negative-case design across the 10 negative cases · the three hostile-narrative shapes (`CLM-8941`, `CLM-8952`, `CLM-9035`) · D7 failure reproduction and re-runs | review of the judge parser, harness, loop and cost model · live model `google/gemini-2.5-flash` |
| **Zhao Yujia** | D0 *why an agent* — ladder, both Capsule 1 tests, the autonomy defence · D6 cost model alongside Shen Bowen · report assembly · demo coordination · technical PM | `src/cost_model.py` and its refusal of null inputs · **the D2(b) v1 pass**, `qwen/qwen3-235b-a22b-2507`, prompt v1 — the only measurement in A2 that isolates our own writing as the variable |

**Two things the history cannot show, stated here instead.** Our 40 evaluation cases were
written in synchronous sessions with all six members present and consolidated through one
committer, because `make_fixtures_A.py` and `expected_outcomes_A.json` are a generator and a
single answer-key file rather than one file per author — two people editing them in parallel
produce a merge conflict in a JSON object whose key order the generator depends on. We would
choose one file per author next time. Separately, Li Yunke's and Zhao Yujia's battery rows
were committed under Rohit's name; both members ran their own battery on their own key.

---

## 6 · Declaration

*Every member ticks every box. One sheet, signed by the team.*

> **These boxes are unticked on purpose.** Each is a statement only a member can make about
> their own knowledge and their own work. Read each one, tick it if it is true of you, and do
> not tick any box on someone else's behalf.

- [ ] Every member of this team can explain every block of code we submit — what it does, and why it is there. *(Block, not line: this is about function, not syntax.)*
- [ ] The pass rates, token counts, turn counts and costs we report are measurements we ran ourselves. None of them were supplied by an AI assistant.
- [ ] Our submitted harness runs end to end on the scripted backend, with no key and no network.
- [ ] We kept every fixture record we were given, unedited, and every case in our evaluation set carries a label. `check_my_data.py` passes on our data.
- [ ] No part of this submission is drawn from any member's End-of-Course Project, and no part of it will be submitted as part of one.
- [ ] This is our own work, and all sources, tools and assistance are attributed.

**Signed on behalf of the team:** `______________________________`  **Date:** `____________`

> **Before you tick box 2,** note that it is about *measurements*, not about authorship of
> code. Every figure on this sheet was produced by our own harness and can be reproduced from
> the repository. Our use of AI assistance in building the system is attributed in
> `CONTRIBUTIONS.md` §4, which is what box 6 requires — keep that section in place.
>
> **Before you tick box 3,** it is true as of commit `2ac036d`: `BACKEND = "scripted"` is the
> committed default, the project is standard-library only, and `python3 run_eval.py` returns
> 60/60 from a clean clone with `OPENROUTER_API_KEY` unset.
>
> **Before you tick box 4,** run `python3 data/check_my_data.py` once more on the final tree
> so the claim is current rather than remembered.
