# CLAUDE.md — PE6201 A2 Project Blueprint & Execution Plan

> **Repository operating document.** Read this before writing any code, opening any PR,
> or running any live model. Constraints and prohibitions live in `GUARDRAILS.md` —
> that file overrides this one wherever they appear to disagree.
>
> **Filename note:** keep this as `CLAUDE.md` (uppercase) at repo root so Claude Code
> auto-loads it as project context.

**Course:** PE6201 Emerging AI Technologies · MSc Enterprise AI · T1 AY2026–27
**Assessment:** A2 — Applied AI System · Group · 20% of course grade · Rubric 1
**Problem:** A — Health-insurance claim first response
**Team:** 6 members · Team ID: `<FILL>` · Section: `<FILL>`
**Repository:** `<FILL — required on the Team Declaration by Fri 4 Sep>`

Source tags used throughout: `[brief]` = PE6201_A2_Applied_AI_System.pdf ·
`[faq]` = PE6201_A2_FAQ.pdf · `[upd]` = PE6201_A2_Document_Updates.pdf ·
`[lect]` = lecturer briefing notes · `[team]` = our decision, not prescribed.

---

## 1 · Executive summary

### What A2 actually is

A2 is not "build an agent." It is **build a modest agent and prove what it does and
what it costs.** `[brief §5]` states the marking posture directly: *an agent that does
more, proved less, scores lower than an agent that does less, proved properly.*

The submission has to answer three questions about the same system:

| Week | Class | The question | Deliverables it feeds |
|---|---|---|---|
| 4 | The loop, tools, guardrails, eval set | **Does it work?** | D0, D1, D2, D3, D4 |
| 5 | Cost-to-serve and ROI | **What does it cost when it doesn't?** | D6 |
| 6 | Responsible AI, failure modes | **What happens when someone attacks it?** | D3(b), D7 |

### The architecture, fixed by the brief

- Single-agent **ReAct** loop: Thought → Action → Observation → repeat → Final. `[brief D1]`
- Hand-rolled. No framework may own the loop. `[brief D1]` `[lect]`
- Must parse and execute **multiple tool calls in one turn**. `[brief D2(c)]` `[lect]`
- Rung 7 on Class 4's ladder — the brief chose the rung; our job is to defend what
  rungs 1–6 would and would not have delivered. `[brief D0(a)]`
- Gated action: `issue_decision_letter` — **one log line, not a letter.** `[brief D1]`

### Problem A in one paragraph

A claim carries several line items, each with a procedure code and amount, each checked
in its own right. The agent checks the policy is live, works each line, chases a
pre-authorisation where the procedure requires one, checks whether the hospital is on
panel, then reaches exactly one of three outcomes: **approve in principle · request a
specific missing document · escalate to a human assessor.** `[brief App. A]`

**The distinction that carries marks:** a partly payable claim is still an *approve*, not
an escalation. Three lines approved and one excluded is one decision letter covering
both. Escalate when the *claim* cannot be decided — not when a *line* is refused.
`[brief App. A]`

### The eight deliverables

| ID | What | Primary owner | Runs on |
|---|---|---|---|
| D0 | Why an agent at all — ladder, two tests, what good looks like | M6 + all | writing |
| D1 | The ReAct agent | M1 | code |
| D2(a) | Tool set, scored against the three questions | M1 + M2 | design |
| D2(b) | Six-field descriptors, ≥2 poka-yoke moves, v1→v2 measured | M2 | design + 1 live pass |
| D2(c) | Multi-tool turns, dependency rule, measured both ways | M1 | scripted |
| D3(a) | Guardrail **code** layer | M2 | code |
| D3(b) | Guardrail checklist — ≥10 cases, ≥3 hostile text | M2 + M5 | **scripted, free** |
| D4 | Evaluation set — 40 cases, 8 negative, all members author 5–8 | **all** | scripted + live |
| D5(a) | Reproducible scripted end-to-end run | M3 | **scripted, free** |
| D5(b) | Live model battery — one model per member | **all** | **live (only paid part)** |
| D6 | Three-layer cost model, four levers, sensitivity, break-even | M4 | analysis |
| D7 | Two reproduced failures, one a loop failure | M5 | **scripted, free** |

**Only D5(b) and D2(b)'s v1 pass spend money.** `[upd]` D3(b), D5(a) and D7 all run on
the scripted backend at zero cost. If you find yourself burning live tokens on those
three, stop.

---

## 2 · Timeline and gate conditions

| Date | Gate | Blocking condition |
|---|---|---|
| Wed 2 Sep, midday | Fixture generator + starter scaffold on NTULearn | — |
| **Wed 2 Sep (today)** | **D0(c) committed** | Must land **before the first agent-code commit** `[brief D0(c)]` |
| Thu 3 Sep | Tool set frozen, descriptors v1 drafted, repo URL live | Declaration needs the URL |
| **Fri 4 Sep, 23:59** | **TEAM_DECLARATION checked into submission folder** | Not an email. `[brief §8]` Eval set should be written by now `[brief §10]` |
| Sun 6 Sep | Loop + scripted backend green end to end | Blocks D3(b), D7 |
| Mon 7 / Tue 8 Sep | Class 6 — sharpens D3(b), does not start it | Do not wait for it `[brief §10]` |
| Tue 8 Sep | 40 cases + answer key complete; guardrail checklist passing | Blocks battery |
| **Wed 9 Sep** | **`v2-freeze` tag cut** | Nobody merges to `main` until battery lands |
| Wed 9 – Thu 10 Sep | Live battery: 6 members × 56 runs | Blocks D6 |
| Fri 11 Sep | D6 cost model, sensitivity, break-even complete | Blocks report §4 |
| Sat 12 Sep | Report at 2,000 words; demo recorded; self-appraisal signed | — |
| **Sun 13 Sep, 23:59** | **A2 due** — zip, repo, report, self-appraisal, video link | — |
| Wed 16 Sep, 23:59 | Peer rating (participation requirement) | — |
| Sun 27 Sep, 23:59 | End-of-Course Project — **do not let A2 eat this** `[brief §10]` | — |

---

## 3 · Phase plan

### Phase 0 — Foundation (2 Sep, today) · owner M6 coordinates

This phase is **entirely writing**. None of it needs the scaffold. `[brief §2]`

1. Create the public repo. Commit `README.md`, `CLAUDE.md`, `GUARDRAILS.md`,
   `CONTRIBUTIONS.md`, `.gitignore`.
2. Write `docs/D0c_what_good_looks_like.md` — **five numbered statements**, each
   testable, committed **before any agent code**. Copy the shape from `[brief D0(c)]`:
   names the real cause traceable to a record · outcome consistent with the records ·
   gated action at most once and only after the facts · says "I don't know" rather than
   inventing · costs less than a person. Item 4 is the one teams forget and the one the
   negative cases exist to catch.
3. Write `docs/D0_why_an_agent.md` skeleton — ladder placement, the four-row workflow
   test, the two conditions, the three-question test naming our first irreversible action.
4. Draft the Team Declaration. Fill sections 1, 2, 4, 5. Section 5 is marked NOT
   OPTIONAL — state explicitly "All members are contributing" or name the problem.

**Exit condition:** `git log` shows `docs(d0)` commits with timestamps earlier than the
first `feat(loop)` commit.

### Phase 1 — Tool layer design (2–4 Sep) · M1 + M2

1. **D2(a) — score every tool** against the three questions in a repo table:
   does a task fail without it · could the model confuse it with a neighbour · what does
   it cost when never called (its definition sits in the prefix and is re-billed every
   turn). `[brief D2(a)]`
2. **Before adding a tool, try not adding one** — four moves in order of preference:
   widen an existing tool's parameters · return more from one call · move the step into
   ordinary code outside the loop · only then add the tool. Record which we tried.
3. **Ship the shortest defensible list.** The brief credits four justified tools over
   eleven, and gives *explicit credit* for a tool removed with the observation that
   removed it. `[team]` Our starting six are minimums from Appendix A, not an interface:
   `get_claim` · `lookup_policy` · `check_coverage` · `get_preauthorisation` ·
   `get_hospital_status` · `issue_decision_letter`. Rename, merge, split or drop as our
   scoring dictates — the names in Appendix A are suggestions. `[upd]`
   **Find our `search_notes`** — the tool that fails questions 1 and 2. If we cannot name
   one, we have not scored honestly.
4. **D2(b) — six-field descriptor per tool, no exceptions:**
   `NAME + SIGNATURE` · `WHAT` (one line, what this answers that nothing else does) ·
   `INPUT` (each arg, type, what a bad value does) · `RETURNS` (shape **with a size
   bound**) · `FAILS WHEN` · `IRREVERSIBLE?` (yes/no, and the gate if yes).
5. **At least two poka-yoke moves**, each stated as *what it makes impossible*, not what
   it discourages. Candidates for Problem A `[team]`:
   `site: str` → `site: Literal[...]` · `member_name` → `member_id` ·
   `issue_decision_letter(..., autonomy="confirm")` as the safe default ·
   `procedure_code: str` → validated against the procedures fixture at the boundary.
6. **D2(c) — write the dependency rule down** before coding it. A pair may go in parallel
   only when neither needs the other's output. Our reading `[team]`, defensible not
   prescribed:
   - Turn 1 alone: `get_claim` — everything downstream needs the member, hospital and lines.
   - Turn 2 parallel: `lookup_policy` ‖ `check_coverage` × N lines ‖ `get_hospital_status`.
   - Turn 3: `get_preauthorisation` — cannot parallelise; we don't know which line needs
     one until coverage answers.
   - Turn 4: `issue_decision_letter` — a turn like any other; gated, not free.

   **We must state our rule, measure both ways, and show correctness did not move.**
   `[upd]` A team that parallelises *less* than the brief's example and explains why is on
   stronger ground than one that copied the page. Report our own measured saving. Do not
   quote 54% — that is CLM-8842's number, not ours.

### Phase 2 — Build (4–8 Sep) · M1, M2, M3

1. **M1 — `src/loop.py`.** Parse an `Action:` *block*, execute each call, append each
   observation, then ask again. Instrument per run: turns used, tokens in/out, estimated
   cost, whether a cap fired, tools called in order. Without this D7 is impossible —
   *"you cannot report a failure you had no way of noticing."* `[faq]`
2. **M1 — `src/backends/scripted.py`.** Deterministic canned responses, no network, no
   key. `BACKEND = "scripted"` is the **default in submitted code** or Technical
   Execution is capped. `[brief D5(a)]`
3. **M1 — vendor neutrality.** One `BACKEND / MODEL / BASE_URL` block at the top of
   `src/config.py`, and *exactly one function that knows a vendor exists.* Switching model
   is a string. `[brief D5(b)]`
4. **M2 — `src/guardrails.py`, shipped before any prompt tuning:** step cap · budget
   ceiling · action de-duplication · explicit autonomy setting. `[brief D3(a)]`
   Guardrails live in **code, not the prompt.**
5. **M2 — autonomy setting.** `[team]` Recommend `confirm` for Problem A: the gate sits
   in front of `issue_decision_letter`, not in front of the agent as a whole. Defend it
   in the report against the irreversible step, not by taste.
6. **M3 — `eval/harness.py`** with both grader kinds:
   - **Code check** — harness compares against the answer key. The `decision` field, the
     single `trigger`, the named missing item, whether the gated action fired exactly
     once. No model, no person, free, deterministic.
   - **Judgement check** — a person or a *second* model reads the record. Use only where
     correctness is not a comparison: is the stated reason actually a reason, does the
     evidence trail support the decision.
   - The split, in one line: **decision and trigger are code checks; wording is a
     judgement check.** `[brief D4]` Our results table must say which check each case used.
   - If a model judges: name it, commit the prompt, and use a **different model from the
     one being graded.** `[brief D4]`
   - **The trap:** a substring check that passes for the wrong reason. Check the thing we
     care about, not a string that usually accompanies it. `[faq]`
7. **M3 — token/cost estimation on the scripted path.** Scripted runs must still emit
   token counts (via a tokeniser) priced off the `[brief §7]` table, because D7's
   before/after tables come from scripted runs.

### Phase 3 — Evidence (6–9 Sep) · all

1. **D4 — 40 cases, 8 negative, everyone writes 5–8.** Non-negotiable row on the
   declaration. A set written by one head tests one head's assumptions. `[faq]`
   - Negative-case families for Problem A `[brief App. A]`: policy lapsed or out of dates ·
     one line excluded while others are fine · pre-auth required and absent, or expired
     before date of service · lines together exceed remaining annual limit · duplicate of
     a claim already decided · **narrative instructing the system to approve.**
   - Each negative case must **name the wrong behaviour it exists to catch.**
   - **Isolation:** every case starts from a clean state. No case may depend on another
     having run.
   - Include a case that rewards **early exit** — the escalate example stops at two turns
     once the limit is breached, because pricing lines it will never pay is burned turns.
2. **D3(b) — the guardrail checklist, ≥10 cases, ≥3 on hostile request text.** Different
   from evaluation cases: an eval case asks *did it get the job right*, a guardrail case
   asks *did it refuse, cap, or escalate.* Run on the scripted backend. `[brief D3(b)]`
   **Caveat to state in the report:** a scripted run proves the guardrail fires when the
   agent *attempts* the bad action. It cannot tell us whether a live model is talked into
   attempting it — that is a D5 observation, not a guardrail case. `[upd]`
3. **D7 — two failures, each built as a deletion from the working agent.** A separately
   written "bad agent" does not count. `[faq]`
   - **Failure 1 (required): loop control.** Delete the de-duplication guard. Report: the
     instrumentation that found it · the **turn distribution** across the whole eval set
     (median, worst case, how many runs hit the cap — one number is not a distribution) ·
     which of the three code guards actually caught it and why the other two would not ·
     before/after turns, tokens, cost **and pass rate** (a step cap that stops a runaway
     also truncates a legitimate long run — show the pass rate did not fall).
   - **Failure 2: a different layer** — tool interface or prompt, not loop control again.
   - For both: state which layer the fix belongs in **and why the other two were wrong.**
     That judgement is most of the mark.
4. **Set the caps from evidence.** After the scripted distribution exists, derive the step
   cap from the worst legitimate run and the budget ceiling from measured per-run cost.
   `[brief D7]` A round number is decoration. **Make the stop loud** — a cap that silently
   returns an empty answer converts a visible cost problem into an invisible correctness one.

### Phase 4 — Battery (9–10 Sep) · all

1. Cut tag `v2-freeze` on `main`. Announce it. Nobody merges until results land.
2. Every member runs **56 runs** on **their own key** against the **identical eval set and
   identical v2 prompt**, from the frozen commit. `MODEL` is the only string that differs.
   *With six runners, drift silently voids the whole battery.* `[brief D5(b)]`
3. M6 runs the **v1 pass** on a model **already in the battery** — comparing prompt
   versions means holding the model fixed. This is not a lesser job: it is the only
   measurement in A2 that isolates our own writing as the variable. `[brief D5(b)]`
4. Each member commits their raw results file under `results/live/`. No editing of numbers.

### Phase 5 — Argue (10–13 Sep) · M4, M6

D6, the report, the demo, the self-appraisal. See §6 and §7.

---

## 4 · Repository layout
/README.md                      clone → scripted run in ≤5 commands, no key
/CLAUDE.md                      this file
/GUARDRAILS.md                  constraints — overrides this file
/CONTRIBUTIONS.md               who did what; commit history must corroborate
/TEAM_DECLARATION.pdf           checked in by Fri 4 Sep
/requirements.txt               pinned
/docs/
  D0_why_an_agent.md            ladder, workflow test, two conditions, three questions
  D0c_what_good_looks_like.md   five statements — FIRST COMMIT, before any agent code
  D2a_tool_scoring.md           three-question table + what we cut and why
  D2b_descriptors.md            six-field contracts + poka-yoke table + v1/v2 measurement
  D2c_dependency_rule.md        which tools may share a turn, and why
  D3b_guardrail_checklist.md    10+ cases, observed results
  D6_cost_model.md              three layers, four levers, sensitivity, break-even
  D7_failures.md                two failures, before/after, layer justification
  report/                       drafts + final 2,000-word report
/src/
  config.py                     BACKEND / MODEL / BASE_URL — one block, scripted default
  loop.py                       the ReAct loop, multi-action parsing, instrumentation
  guardrails.py                 step cap, budget ceiling, dedup, autonomy gate
  tools/                        one module per tool + descriptor docstring
  backends/scripted.py          deterministic, no network, no key
  backends/openrouter.py        the ONLY file that knows a vendor exists
/data/
  shipped/                      READ-ONLY. Never edit or delete a shipped row.
  extended/                     our added rows, new ids only
  expected_outcomes_A.json      answer key
  generate_cases.py             reproducible generator for our additions
/eval/
  cases/                        40 cases, one file per author
  harness.py
  graders/code_check.py
  graders/judge.py              judge prompt committed alongside
/results/
  scripted/                     D3(b), D5(a), D7 outputs — free, deterministic
  live/                         one file per member per model
  v1_vs_v2/
/logs/decisions.jsonl           the gated action's append-only record


---

## 5 · Delegation matrix

Two rows are **not optional** on the declaration: everyone writes evaluation cases, and
everyone runs one live model. `[brief §8]` Everything else below is our split and can be
replaced. `[upd]`

| # | Member | Strand | Feeds | Live model |
|---|---|---|---|---|
| 1 | Rohit Panda | Loop, multi-action parsing, instrumentation, scripted backend, tool set | D1, D2(a), D2(c), D5(a) | Cheap tier — family A |
| 2 | Huang Yu | Descriptors, v1→v2 rewrite, guardrail code layer, checklist | D2(b), D3(a), D3(b) | Cheap tier — family B |
| 3 | Li Yunke | Harness, code/judgement graders, answer-key joins | D4, D5(a) | Cheap tier — family C |
| 4 | Shen Bowen | OpenRouter adapter, cost model, ledger, sensitivity, break-even | D6 | Mid tier — family D |
| 5 | Xia Yanran | Negative-case design, red team, D7 failure reproductions | D3(b), D7 | Mid tier — family E |
| 6 | Zhao Yujia | Technical PM: declaration, D0 drafting, report assembly, demo | D0, report §§1–6 | **v1 pass** on M1's model |
| — | **All** | 5–8 evaluation cases each; one live battery each | D4, D5(b) | — |

**Model selection rules — check before anyone spends a token:** `[brief D5(b)]`
- Models must span **at least two price tiers**.
- **No two members may take models from the same family.**
- Identical eval set, identical v2 prompt, same commit.
- Prices change; verify current OpenRouter per-token pricing on the day and record the
  date checked. Do not select a model from memory or from the brief's example tiers alone.

### Budget — the arithmetic that constrains the battery

| Tier | Price in/out (US$/M) | One run | 56 runs |
|---|---|---|---|
| Cheap | 0.10 / 0.40 | ≈ $0.005 | **≈ $0.27** |
| Mid | 1.00 / 5.00 | ≈ $0.049 | **≈ $2.76** |
| Frontier | 5.00 / 25.00 | ≈ $0.246 | **≈ $13.78** |

`[brief §7]`

- The key is **US$10 for the whole course**, no top-ups, already partly spent on A1, and
  it must still cover the End-of-Course Project due 27 Sep.
- **A full frontier battery exceeds the entire course allowance.** If we want a frontier
  model in the comparison, run it on the **negative cases only** (8 × 3 = 24 runs) and say
  so in the report. `[brief §7]` `[team]` Recommendation: skip frontier entirely — 24
  frontier runs is still ≈ $5.90 and buys one data point.
- Our allocation (3 cheap + 2 mid + 1 v1 pass) puts every member under the brief's
  US$3-per-member warning line, with mid-tier members at ≈ $2.76.
- **Debug on the scripted backend.** Live tokens are for the final battery only.

---

## 6 · The measurement spine

Four formulas connect D0, D2(c), D4, D6 and D7. They are **one argument measured three
times**, not separate exercises. `[brief D0(b)]`

**1 · Token growth per run** — `T` is turns in ONE run, never cases or trials.
```
Class 4 form:  input ≈ B*T + D*T²/2
Class 5 exact: input  = B*T + D*T(T-1)/2      ← the brief's worked examples use this
```
Say which we used. The brief's Problem A example: B=1,200 · sequential T=8, D=400 →
9,600 + 11,200 = 20,800 · parallel T=4, D=800 → 4,800 + 4,800 = 9,600. Note *where* the
saving comes from: the prefix term halved, the quadratic term fell by more than half.
**These are the brief's numbers. Report ours.**

**2 · Implied per-step reliability** — worked backwards, never measured directly.
```
s = P^(1/T)          P = measured pass rate (D4), T = measured median turns (D7)
```
Do **not** multiply the pass rate by itself. `P` is already the output of the compounding.
`[faq]` Treat `s` as a diagnostic answering one question: **is our problem step quality or
step count?** Then say which our evidence points at, and name the weak step by grouping
failing runs by the tool call that immediately preceded the failure.

**3 · Pass rate** — always with its trial count, model, prompt version and date.
```
pass_rate = passing_trials / total_trials
40 cases: 32 ordinary × 1 + 8 negative × 3 = 56 trials
```
> Weak: "our agent is about 85% accurate."
> Strong: "v2 prompt, `<model>`, 56 trials over 40 cases, 48 passed (85.7%); on the 8
> negative cases alone, 19/24 (79.2%)." **The second number is the one that matters.** `[faq]`

**4 · Cost-to-serve — Class 5's escalate-on-failure form, not Class 4's retry form.**
```
layer 1 variable = input*price_in + output*price_out + retrieval + tool fees
layer 2 fallback = (1 - success_rate) * failure_cost
cost per successful task = layer 1 + layer 2
monthly = cost per successful task * volume + layer 3
```
Problem A constants: **volume 8,000 claims/month · failure_cost = $38/h × 12 min ÷ 60 =
US$7.60** (human claims assessor). `[brief App. A]`
A wrong outcome goes to a person, not back into the loop — so the escalation form is
correct here. State that in one line. `[faq]`

**5 · Break-even success rate for the cheap model**
```
failures you can afford   = (E - C) / F
break-even success rate p = 1 - (E - C) / F
```
`C` = one cheap run, tokens only · `E` = one successful task on the expensive model,
**including its own failures** · `F` = US$7.60. The asymmetry is deliberate: the cheap
model's success rate is the unknown we are solving for, so it cannot appear on that side.
`[brief D6]`

**The four levers, each with a measured before and after** `[brief D6]`:

| Lever | Attacks | Built in | Report |
|---|---|---|---|
| 1 · Tool block size | `B` — re-sent every turn, called or not. Linear in T. | D2(a) | tokens of tool definitions, before/after cuts |
| 2 · Turn count | The quadratic term. Biggest lever. | D2(c) | turns + input tokens, sequential vs parallel |
| 3 · Observation size | Compounds — re-sent on every later turn. | D2(b) | tokens returned per call, v1 vs v2 |
| 4 · Success rate | Sets layer 2, usually the biggest layer. | D4 | pass rate and the cost per successful task it implies |

Levers 1 and 3 look similar and are not: a fat tool block is linear, a fat observation
compounds. **Say which dominated our bill and how we know.** Then state the three caps
that ship with it: step cap, budget ceiling, monthly limit per user.

**Sensitivity, not a point estimate.** Show cost per successful task across success rate
± 10 percentage points and say whether the conclusion survives the whole range.

**Caching and reasoning models:** neither belongs in the baseline. If used, measure —
do not model — and report both figures. `reasoning: exclude = true` hides the tokens and
still bills them; it is a tidiness setting, not a cost control. Recommendation from the
brief: **don't use a reasoning model for A2.** `[brief D6]`

---

## 7 · Report, demo and submission

### Report — hard cap 2,000 words of prose

Tables, figures, captions, code, references and the contribution log **do not count**.
`[faq]` Per-section budgets are guidance; the total is a limit.

| § | Section | Content | Words |
|---|---|---|---|
| 1 | Why an agent | D0 — the rung, what rungs 1–6 would/wouldn't have delivered, both tests, our own `s = P^(1/T)` figure, what good looks like | 400 |
| 2 | The tool layer | D2 — why this set and **what we cut**, what the descriptor rewrite measured, dependency rule, what parallel calling saved | 450 |
| 3 | What the evidence showed | D4 + D5 — pass rates, where models diverged, what the negative cases caught | 350 |
| 4 | What it costs | D6 — four levers and which dominated, monthly figure at 8,000/month, sensitivity, break-even | 400 |
| 5 | The two failures | D7 — the loop failure, detection, fix, before/after; the second failure and why its layer | 250 |
| 6 | What we would not deploy | Limits found + a paragraph on an architecture we did not build: what it would have caught, what it would have cost, why we stayed single-agent | 150 |

Section 1 is read first and read hardest. **A report that opens with what we built rather
than why an agent was the right instrument has skipped the question.** `[brief §4]`

Section 3 must fit five or six models in 350 words: put every model in the **table** and
spend the prose on the spread and the two extremes — the cheapest model that met our bar,
the most expensive one that did not earn its price, and **where the negative cases
separated them.** `[upd]`

Section 6's unbuilt-architecture paragraph is explicitly marked under Reasoning &
Justification. Evidence is available in Pre-read 5: Cognition's own reversal, and the
finding that in their working version the writes stay single-threaded. `[brief D1]` `[faq]`

### Demo — 5 minutes

The system running · **one negative case shown live** · the numbers · **every member
speaks.** Over-length is penalised under Communication. `[brief §4]`

### Submission artefacts

1. **Code repository in TWO places** — a public GitHub repo, **and** a copy of the same
   code files inside the NTULearn submission folder. Both required.
2. **Team report** — ≤2,000 words.
3. **Recorded demonstration** — 5 min, link.
4. **Team self-appraisal** — **one collective sheet per team**, not one per member.
   Ungraded but required; a missing one is an incomplete submission.

Archive name: `PE6201_A2_[TeamID].zip` — e.g. `PE6201_A2_B-4.zip`.
`CONTRIBUTIONS.md` in the repo, corroborated by commit history.

---

## 8 · Success criteria mapped to Rubric 1

### Conceptual Understanding — 25%

- [ ] Problem placed on the ladder with rung 7 defended: what a single prompt, a fixed
      workflow and read-only agentic retrieval would and would not have delivered, and
      what the climb cost.
- [ ] The workflow test answered with **cases from our own eval set** showing step count
      genuinely varies with input.
- [ ] Both Capsule 1 tests answered honestly — ground-truth test naming the systems of
      record that can contradict the model *at machine speed* (the policy row, the
      pre-auth record, the hospital panel status) and how fast each answers.
- [ ] The governance cliff named: **agentic retrieval → agent, at the first write.** Our
      first irreversible action is `issue_decision_letter`.
- [ ] Evaluation case vs guardrail case distinction held **throughout**, not just defined.
- [ ] Autonomy setting chosen against the irreversible step, not by taste.
- [ ] `s = P^(1/T)` computed from our own P and T, with its limits stated (steps are not
      independent; not every step is equally failure-prone).

### Technical Execution — 30%

- [ ] **The scripted run reproduces from a clean clone with no key.** `BACKEND =
      "scripted"` is the default. *Failure here caps this criterion.*
- [ ] Turns and cost instrumented **per run** — the loop failure was detected, not assumed.
- [ ] Gated action logs decision + reason + evidence trail + gate + turns + cost to
      `decisions.jsonl`. **No letter text, no template, no prose.**
- [ ] The loop genuinely executes several tool calls in one turn.
- [ ] Every tool carries a full six-field descriptor with real poka-yoke moves **in the
      signatures**.
- [ ] Eval set is isolated, outcome-graded, multi-trial, with real negative cases.
- [ ] **Guardrails in code, not in the prompt.**
- [ ] Live battery ran; the numbers are the ones the code produced.

### Reasoning & Justification — 25%

- [ ] An argued paragraph on an architecture we did **not** build, with evidence.
- [ ] Shortest defensible tool list, scored against the three questions, with **at least
      one tool removed** or one documented "we tried not adding it".
- [ ] Descriptor rewrite measured and reported honestly **even if it did not help.**
- [ ] Cost ledger names all four levers and says which dominated.
- [ ] Model choice follows from our own evidence.
- [ ] Both failures located in the right layer, **with the wrong layers named.**

### Communication & Clarity — 20%

- [ ] The report argues; it does not narrate. (A paragraph explaining *how* our loop
      iterates is spent words; a paragraph explaining *why* we capped it at N turns is not.)
- [ ] The demo shows the negative case, not only the happy path.
- [ ] The repo is navigable by someone who was not in our team.
- [ ] Limits stated plainly.

---

## 9 · Open items to email the lecturer — before Fri 4 Sep

The brief pays **Class Participation credit** for acknowledged defects, and says a defect
found on 2 September helps 27 other teams. `[brief §2]` Send these as one email, phrased as
*what we found, where, and what we expected instead.*

1. **D4 negative-case floor contradicts itself.** The bullet reads "Negative cases — 2 is
   the floor"; the D4 run table gives 6 as the minimum, and the FAQ's negative-case table
   says 6–10. The Document Updates "What did NOT change" section repeats "at least two
   negative cases." Which is the floor?
2. **Section 7 and the D5 table describe different team shapes.** §7 says *"whoever owns
   the cheap model carries 112 runs, about US$0.54"* — implying one member runs both v1 and
   v2. The D5 "Who runs what" table assigns the v1 pass to Member 6 as a separate 56-run
   job on someone else's model. In a team of six, is that 5 v2 models + a dedicated v1
   runner, or 6 v2 models with one member doubling up?
3. **Case count.** The verbal briefing suggested 50–60 test cases; the brief and FAQ
   specify 30–50 with 40 as the expected shape, and the run arithmetic is written against
   40. Confirming 40 is the target we are graded against.
4. **Frontier tier.** Confirming that a frontier model run on negative cases only (24 runs)
   is reported as a partial pass rate clearly labelled as such, not as a battery result.

Log the answers in `docs/lecturer_clarifications.md` with dates. If no reply arrives,
**document what we found, state what we assumed instead, and carry on** — the brief says
a documented workaround is a strong answer, not a compromised one. `[brief §2]`
