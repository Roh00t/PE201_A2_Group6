# GUARDRAILS.md — Constraints & Operational Rules

> **This file overrides `CLAUDE.md` wherever they appear to disagree.**
> Read before your first commit. Re-read before the `v2-freeze` tag.
>
> Every rule below traces to a source: `[brief]` PE6201_A2_Applied_AI_System.pdf ·
> `[faq]` PE6201_A2_FAQ.pdf · `[upd]` PE6201_A2_Document_Updates.pdf ·
> `[lect]` lecturer briefing · `[team]` our own operating decision.

---

## 1 · Architecture boundaries

### Prohibited — these are scope rules, not difficulty rules

| Prohibited | Why | Source |
|---|---|---|
| **Any framework that owns the loop** — LangChain, LangGraph, CrewAI, AutoGen and relatives | The loop is the thing being marked. If a library runs it, there is nothing of ours to assess in D2(c) or the guardrail layer. | `[brief D1]` `[faq]` `[lect]` |
| **Multi-agent systems** — orchestrators, agents calling agents, specialist handoffs | Class 4 compared the patterns and built exactly one. We are not marked on what we were not taught to build. | `[brief D1]` `[faq]` |
| **Sub-agents used to widen the tool set** | Same reason — it would hide the loop A2 is marking. | `[brief D1]` |
| **Fine-tuning** | Not taught, not affordable on a US$10 key, not what this assignment is about. | `[brief D1]` |
| **Any tool taking a real-world irreversible action** — real email, real payment, real booking, writing to any live system | Hard rule. Class 4's notebook simulated its single write for exactly this reason. | `[brief D1]` |

**Permitted and expected:** ordinary libraries for everything that is not the loop — data
handling, HTTP, testing, plotting, tokenisers. `[faq]`

**Arguing about the prohibited architectures earns marks.** Report §6 must contain a
paragraph on what a second agent would have caught, what it would have cost, and why we
stayed single-agent. Marks for the argument, none for the unbuilt architecture. `[brief D1]`

### Web/public-API tools — optional, conditional, and probably wrong for us

Permitted, never required, rarely the right call. Both problems are answered from their
own records. Under D2(a)'s question 1 a search tool usually fails: *name the task that
fails without it.* If we cannot, cut it. `[faq]`

**If one is added, one condition is not negotiable:** the scripted run must still
reproduce with **no network and no key**. Call the service once, commit the responses as
fixtures, replay them from the scripted backend. A live call inside the evaluated path
means the same case passes on Tuesday and fails on Thursday, which makes the pass rate —
and the whole cost model that divides by it — meaningless. `[brief D1]` `[faq]`

`[team]` **Default position: no external tool.** Adding one requires a written D2(a)
justification merged to `main` first.

---

## 2 · Scope boundaries — what we are NOT building

**None of the following earns a single mark, and every one is a way to run out of time.**
`[brief D1]` `[faq]` `[lect]`

- A letter or document generator · templated customer prose
- PDF or Word output
- A user interface of any kind · a web front end · a mobile app · a login or user accounts
- **Streamlit or any other app** — *"You are here for AI. You are not here for web design."* `[lect]`
- A database server · MySQL · anything deployed anywhere
- A booking or appointment application · calendar or scheduling integration
- Real email sending

### The single most expensive misunderstanding available to us

**The gated action is a log entry, not the thing it stands for.** `issue_decision_letter`
does **not** write a letter. It is one function, three steps:

1. Check the gate — is the autonomy setting satisfied, has the operator confirmed.
2. Append **one structured record** to a local file.
3. Return a confirmation string, ≤30 tokens.

```python
def issue_decision_letter(claim_id, decision, reason, evidence, autonomy="confirm"):
    """WHAT     Records the first-response decision on a claim.
       INPUT    claim_id str; decision Literal["approve_in_principle",
                "request_document","escalate"]; reason str; evidence list[str]
       RETURNS  confirmation str, <= 30 tokens
       FAILS WHEN the gate is not satisfied, or claim_id already has a decision
       IRREVERSIBLE? YES - covered by the autonomy gate below."""
    if autonomy == "confirm" and not operator_approved(claim_id):
        return "BLOCKED: awaiting operator confirmation"
    if already_decided(claim_id):
        return "BLOCKED: duplicate - a decision already exists"
    append_json("decisions.jsonl", {...})
    return f"recorded: {decision} on {claim_id}"
```
`[faq]`

**Weak:** a function that renders a formatted letter with a greeting and a policy summary.
**Strong:** the above — the decision, why, which tools evidenced it, which gate let it
through, what it cost. *Nothing in Rubric 1 marks the prose the decision would have
produced.* `[faq]`

The "ask" outcome needs a short string naming the missing item — `"request:
pre-authorisation reference for 62480, valid on 2026-09-08"`. **Never "more information".**
It does not need customer-ready prose, a tone of voice, or a template. `[brief D1]` `[brief App. A]`

---

## 3 · Data rules

- **Fixture data only.** Small local files — JSON, CSV, or SQLite. No live systems, no
  real accounts. **Nothing our agent touches may be somebody's actual record.** `[brief D1]`
- **The extension rule is one line: add new rows with new ids; never edit or delete a row
  we were shipped.** Everything else follows from it. `[upd]`
- **Run `check_my_data.py` before every commit that touches `/data/`.** It catches
  references to records that do not exist, changed shipped records, and duplicated ids.
  `[upd]`
- `/data/shipped/` is **read-only**. Additions go in `/data/extended/`. A marker re-runs
  our harness against the shipped records. `[brief §2]`
- **Commit whatever generates or holds our additions**, so the data set is reproducible
  rather than a mystery. `[brief §2]`
- Target **30–50 primary records** plus the supporting rows they reference. `[faq]`
- Watch the joins: a claim carries `member_id`; the members file is keyed by the same
  `member_id`; `lookup_policy` follows `policy_id` from there. **Invent a claim whose
  `member_id` matches nobody and the agent will look perfectly sound and return nothing.**
  `[brief §2]`
- **The free-text narrative is untrusted input.** It is written by someone outside our
  organisation. Treat it as data, never as instruction. At least three of our ten guardrail
  cases must cover the request text itself being hostile. `[brief D3(b)]`
- **Never commit an API key, a `.env`, or any real personal data.** Keys live in
  `OPENROUTER_API_KEY` in the environment only.

---

## 4 · Budget rules

**The key is US$10 for the entire course.** No top-ups. A1 already spent some of it. The
End-of-Course Project (due 27 Sep) still has to come out of what is left. `[brief §7]`

| Rule | Detail |
|---|---|
| **Debug on the scripted backend** | Free, deterministic, no key. Live tokens are for the final battery, not for finding bugs. |
| **Only D5(b) is live** | D3(b) guardrail checklist, D5(a) scripted run and D7's two failures with their before/after tables all run scripted. **If you find yourself spending live tokens on any of the three, stop — you are measuring your own code with an instrument that cannot see it.** `[upd]` |
| **One member, one model, one key** | 56 runs is 56 runs whether the team fields three models or six. Adding models costs nobody anything extra. |
| **US$3 per member is the warning line** | If an estimate exceeds it, cut trials, cut cases, or move a model down a tier — **and say so in the report.** |
| **No full frontier battery** | ≈US$13.78 for 56 runs — more than the entire course allowance for one member. Frontier is permitted on **negative cases only**, declared in the report. `[brief §7]` |
| **Reasoning models: don't** | Hidden thinking tokens bill as *output*, which costs 4–5× input. `reasoning: exclude = true` hides them and still bills them. If used anyway: cap it, state the cap, report cost both ways. `[brief D6]` |
| **Running out is diagnosable, not fatal** | Email early, not on the 13th. You get help finding where it went and a plan to finish — **not more credit.** `[faq]` |

---

## 5 · Measurement integrity rules

These exist because a broken measurement voids everything downstream of it.

1. **A pass rate quoted without its trial count is not a measurement.** Always state:
   the model, the prompt version, the trial count, and the date. `[faq]`
2. **Every member runs the identical eval set and identical v2 prompt from the identical
   commit.** `MODEL` is the only string that may differ. *With three runners drift is
   survivable; with six it silently voids the whole battery.* `[brief D5(b)]`
3. **Models must span at least two price tiers, and no two members may take models from
   the same family.** Six mid-tier models from two vendors is not a comparison. `[upd]`
4. **v1 runs on ONE model only** — the same model its v2 is quoted against. To compare
   prompt versions, hold the model fixed; to compare models, hold the prompt fixed.
   **Change one thing at a time or the difference is not attributable to anything.**
   Running v1 on every model buys nothing and multiplies the bill. `[brief D4]`
5. **`T` is the number of turns in ONE run.** Never the number of runs, cases or trials.
   `0.95^20` is twenty steps inside one trajectory, not twenty test cases. `[brief §11]`
6. **Never multiply the pass rate by itself.** `P` is already the output of the
   compounding, not the input. Raising `P` to the power of `T` again is the most common way
   to get this wrong. `[faq]`
7. **Grade the field, not by taste.** A field whose correct value comes from a fixed list —
   the decision, the trigger, the named missing item — is a **code check, always.** Prose is
   a judgement check. `[faq]`
8. **A model judge is a measuring instrument.** Name it, commit the grading prompt, and use
   a **different model from the one being graded.** A model marking its own homework is not
   a measurement. `[brief D4]`
9. **Check the thing you care about, not a string that usually accompanies it.** Class 4's
   credulous agent scored 3/24 instead of 0/24 because one substring check found a date
   inside an answer that was wrong about everything else. `[faq]`
10. **The right outcome by the wrong trigger is not a pass.** It got there by luck and it
    will not get there next time. `[brief §2]`
11. **Cases are isolated.** No case may depend on a previous one having run. `[brief D4]`
12. **Figures in the report are measurements we ran, not numbers a model produced for us.**
    `[brief §6]`
13. **Set caps from evidence, not from a round number.** If the median run is 4 turns and
    the worst legitimate run is 7, a cap of 8 is defensible and a cap of 30 is decoration.
    Same test applies to the budget ceiling. `[brief D7]`
14. **Make the stop loud.** A cap that silently returns an empty answer is worse than the
    loop — it converts a visible cost problem into an invisible correctness one. `[brief D7]`
15. **Use Class 5's cost formula**, `variable + (1-p) × failure_cost`, not Class 4's
    `cost ÷ p`. A wrong outcome here goes to a human assessor, not back into the loop. State
    which world we are in, in one line. `[faq]`

---

## 6 · Academic integrity and artefact separation

- **A2 may not be built on any member's End-of-Course Project**, and no A2 artefact — the
  agent, harness, fixtures, evaluation set, report — may later appear in anyone's Project.
  **Techniques travel freely. Artefacts do not. Nothing may be marked twice.** `[brief §1]`
- A Project idea that *resembles* Problem A is fine and is not a conflict — but the two
  builds must be separate work with separate repositories, separate fixtures and separate
  write-ups. `[brief §1]` `[team]` Anyone whose individual Project sits in healthcare,
  clinical documentation or insurance operations should say so at the first team meeting so
  the separation is deliberate and documented.
- **Using AI to build AI is encouraged, on four conditions:** every member must be able to
  explain **any block** of submitted code — for A2 this is team-wide, any member may be
  asked about any block · figures are measurements we ran · sources and tools are attributed
  · nothing is submitted twice. `[brief §6]`

---

## 7 · Version control standards

### Branching

- `main` is protected. No direct pushes. No force pushes, ever.
- Branch naming: `<initials>/<strand>/<slug>` — e.g. `rp/loop/parallel-actions`,
  `hy/descriptors/v2-rewrite`, `xy/failures/dedup-deletion`.
- Short-lived branches. Merge within 48 hours or the branch is stale.
- One reviewer approval required. Reviewer is the member whose strand the change touches
  most, per the delegation matrix.
- **Merge with a merge commit, or squash with `Co-authored-by:` trailers preserved.**
  Never squash in a way that erases who wrote what — the commit history has to corroborate
  `CONTRIBUTIONS.md`. `[brief §4]`

### Commit message format

```
<type>(<scope>): <imperative subject, ≤72 chars>

<body — why, not what. Reference the observation that motivated the change.>

Refs: D<n>
```

**Types:** `feat` · `fix` · `docs` · `data` · `eval` · `exp` (a measurement run) ·
`test` · `refactor` · `chore` · `revert`

**Scopes:** `loop` · `tools` · `descriptors` · `guardrails` · `harness` · `graders` ·
`data` · `cost` · `report` · `demo` · `repo`

Examples:
```
docs(d0): add five what-good-looks-like statements

Committed before any agent code so the ordering is visible in history.

Refs: D0(c)
```
```
feat(tools): constrain site to Literal["SIN","KUL","HKG"]

Poka-yoke: makes a typo'd site silently returning "no record" impossible.

Refs: D2(b)
```
```
exp(battery): v2 battery on <model>, 56 trials, 48 passed (85.7%)

Negative cases alone: 19/24 (79.2%). Run from tag v2-freeze.

Refs: D5(b)
```

### Ordering rules that the marker will check

1. **`docs(d0)` commits must predate the first `feat(loop)` commit.** The brief says
   explicitly: *"we will look at the commit history."* `[brief D0(c)]`
2. **Everyone commits under their own account.** No one pushes on behalf of an absent
   teammate. Pair work uses `Co-authored-by:`.
3. **Nobody rewrites history on `main`.** Contribution corroboration depends on it.

### The freeze protocol

- Before the live battery, cut and push tag **`v2-freeze`** on `main` and announce it.
- Between `v2-freeze` and the last battery result landing, **no merges to `main`.**
- If a defect forces a change during that window: branch `hotfix/*`, and **every member who
  has already run must re-run**. Announce the invalidation explicitly. A half-frozen
  battery is not a battery.

### Result files — never edit a number

```
results/live/<initials>__<provider>__<model-slug>__v2freeze.json
results/v1_vs_v2/<initials>__<model-slug>__v1.json
results/scripted/<deliverable>__<date>.json
```
Raw harness output only. Analysis and aggregation live in `docs/`, never by hand-editing
a result file.

### `.gitignore` minimum

```
.env
.env.*
*.key
__pycache__/
.venv/
.ipynb_checkpoints/
results/tmp/
logs/*.local
```

---

## 8 · Explicit DO NOTs

Derived directly from the lecturer's warnings, the FAQ and the brief's failure modes.

### Build

1. **Do not use LangChain, LangGraph, or any framework for the loop.** `[lect]` `[brief D1]`
2. **Do not build a Streamlit app, a UI, a database, or a deployment.** `[lect]` `[brief D1]`
3. **Do not compose a letter.** The gated action writes a log record. `[brief D1]` `[faq]`
4. **Do not build a multi-agent system** because it would be more impressive. It is out of
   scope. Argue about it in §6 instead. `[faq]`
5. **Do not put guardrails in the prompt.** Step cap, budget ceiling, de-duplication and
   the autonomy gate are code. A model cannot influence whether our code fires. `[upd]`
6. **Do not add a tool before trying not to add one.** Widen a parameter · return more from
   one call · move the step into ordinary code · only then add. `[brief D2(a)]`
7. **Do not collapse "one line excluded" into an escalation.** A partly payable claim is an
   **approve**, with the excluded line refused inside the same decision. *Teams that collapse
   those two cases lose the distinction the assessor is actually paid for.* `[brief App. A]`
8. **Do not choose our own routing rule.** It is the insurer's policy. We automate it, we
   did not invent it, we may not change it — the answer key is written against it. `[brief §11]`
9. **Do not put a timestamp at the top of the system prompt.** It turns prefix caching off
   without anyone noticing. `[brief D6]`

### Measure

10. **Do not build a separately written "bad agent" for D7.** Each failure must be a
    **deletion from the working agent**; putting X back must recover the behaviour. Otherwise
    you cannot tell whether the fix worked or the rewrite did. `[faq]`
11. **Do not make both D7 failures loop-control failures.** One must sit in the tool
    interface or the prompt. `[brief D7]`
12. **Do not report one number as a turn distribution.** Median, worst case, and how many
    runs hit the cap. `[brief D7]`
13. **Do not file hostile-input tests as evaluation cases.** *"A team that files all its
    hostile-input tests as evaluation cases has a 40-case eval set and an empty checklist."*
    `[faq]`
14. **Do not claim a scripted guardrail run proves a live model resists the attack.** It
    proves the guardrail fires when the agent attempts the bad action. Whether a live model
    is talked into attempting it is a D5 observation. `[upd]`
15. **Do not report a v2 improvement we did not measure.** A rewrite that did not help,
    honestly reported, scores **better** than one that was never measured. `[brief D2(b)]`
16. **Do not copy the brief's 54% parallelisation figure** or its 8→4 turn count as our
    result. Those are CLM-8842's numbers. *"D2(c) marks your reasoning, not your number."*
    `[upd]`
17. **Do not model prompt caching. Measure it** — take token counts from the API response,
    not the price list, and report with and without. `[brief D6]`

### Team and process

18. **Do not let the coders code while everyone else watches.** Conceptual Understanding
    (25%) and Reasoning & Justification (25%) are half the total and almost none of it is
    code. `[brief]`
19. **Do not let one person write the evaluation set.** *"A set written by one head tests
    one head's assumptions."* Everyone writes 5–8. `[faq]`
20. **Do not stay silent on the contribution statement.** Silence on 4 September is read as
    *"all members are contributing."* A team that says nothing at the checkpoint and raises
    the problem on 13 September has a much weaker case — no warning was issued, no
    remediation window existed, no contemporaneous record exists. `[brief §8]` `[lect]`
21. **Do not plan to use A1 feedback as our guide.** Cohort-level A1 analysis is **not being
    run this trimester**, and A2 feedback comes offline after submission. Section 5 of the
    brief is the guide. `[brief §9]`
22. **Do not wait for Class 6 (7–8 Sep) to start the guardrail layer.** It falls five days
    before the deadline. Build from Class 4 material now; let Class 6 sharpen it. `[brief §10]`
23. **Do not choose another feature over another ten evaluation cases.** *"If you are
    choosing between another feature and another ten evaluation cases, write the cases."*
    `[faq]`
24. **Do not sit on a defect.** A defect found on 2 September helps 27 other teams and earns
    Class Participation credit; the same defect on 12 September helps nobody. `[brief §2]`

---

## 9 · Final submission checklist

Work top to bottom on **Sat 12 Sep**, not on the 13th.

### Runtime and reproducibility

- [ ] `BACKEND = "scripted"` is the **default** in `src/config.py`. *Technical Execution is
      capped if the harness does not run this way.* `[brief D5(a)]`
- [ ] Fresh clone into a clean venv → scripted run completes **with no network and no API
      key**. Test this on a machine that never held our key.
- [ ] `requirements.txt` pinned; Python version stated in `README.md`.
- [ ] `README.md` gets a stranger from clone to a reproduced scripted run in ≤5 commands.
- [ ] D3(b) checklist, D5(a) run and D7 before/after tables **all reproduce for a marker at
      zero cost.**
- [ ] No `.env`, no key, no real personal data anywhere in history — check, don't assume.
- [ ] `data/shipped/` byte-identical to what was issued. `check_my_data.py` clean.

### Artefacts

- [ ] **Archive named exactly `PE6201_A2_[TeamID].zip`** — e.g. `PE6201_A2_B-4.zip`.
- [ ] **Repository in two places**: public GitHub repo **and** a copy of the same code
      files inside the NTULearn submission folder. Both required — the repo shows history,
      the folder copy means marking never depends on a link working. `[brief §4]`
- [ ] **Report** — ≤2,000 words of prose, six sections in the prescribed order, starting
      with *why an agent*. Tables and figures excluded from the count.
- [ ] **Demo video link** — 5 minutes, **one negative case shown live**, the numbers, and
      **every member speaks**. Over-length penalised.
- [ ] **Team self-appraisal** — **one collective sheet for the team**, not one per member.
      Ungraded but required; missing it makes the submission incomplete.
- [ ] `CONTRIBUTIONS.md` present, and the commit history corroborates it.
- [ ] `TEAM_DECLARATION` already checked into the submission folder (Fri 4 Sep) — file name
      kept as `TEAM_DECLARATION`, `.docx`/`.pdf`/`.md`.

### Content spot-checks

- [ ] Every pass rate in the report carries its **trial count, model, prompt version and date**.
- [ ] The results table names the **check kind (code or judgement) per case**.
- [ ] Cost model uses the **escalation form**, at 8,000 claims/month and US$7.60 per failure.
- [ ] Sensitivity range shown at success rate ±10 pp, with a stated verdict on whether the
      conclusion survives it.
- [ ] Break-even success rate computed and answered in one sentence with our two measured
      numbers in it.
- [ ] Report §6 contains the unbuilt-architecture paragraph with cost and evidence.
- [ ] Any lecturer clarification we relied on is logged with its date in
      `docs/lecturer_clarifications.md`.

### After submission

- [ ] **Peer rating by Wed 16 Sep, 23:59 SGT** — a participation requirement. `[brief §8]`
- [ ] Repo left public and untouched until marks are released.

---

## 10 · The one thing worth repeating

> *An agent that does more, proved less, scores lower than an agent that does less, proved
> properly. If you are choosing between another feature and another ten evaluation cases,
> write the cases.* `[faq]`

> *Build something small that your whole team understands completely — then prove what it
> does and what it costs.* `[brief App. A]`