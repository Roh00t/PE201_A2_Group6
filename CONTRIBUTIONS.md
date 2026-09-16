# CONTRIBUTIONS

**PE6201 A2 · Applied AI System · Problem A — health-insurance claim first response**
Team ID: `B-6` · Section: `B` · Last updated: **16 September 2026**

> The brief requires this file and requires the **commit history to corroborate
> it**. `[brief §8]` Below, "commits" is what `git log` actually shows on `main`
> today — not what was assigned. Where the two differ, the gap is named rather
> than smoothed over, because a contribution log that disagrees with the history
> beside it is worse than no log.

Reproduce the right-hand column with:

```bash
git log --format='%h|%an|%ad|%s' --date=short
```

---

## 1 · Ownership by strand

| Strand | Deliverables | Owner(s) |
|---|---|---|
| The loop and the tools | D1, D2(a), D2(c) | Rohit Panda, Xia Yanran |
| Descriptors, the v1→v2 rewrite, guardrail layer | D2(b), D3(a), D3(b) | Huang Yu, Rohit Panda |
| Evaluation harness and the scripted run | D4, D5(a) | Li Yunke, Huang Yu |
| Cost model, ledger, sensitivity | D6 | Shen Bowen, Zhao Yujia |
| Evaluation cases — **everyone, 5–8 each** | D4 | **All six** |
| Live model battery — **everyone, ONE model each** | D5(b) | **All six** |
| Report and demo assembly | Report §§4–5 | Zhao Yujia, Shen Bowen |

The last two rows are **not optional** on the Team Declaration. `[brief §8]`

---

## 2 · What each member did, and what the history shows

### Rohit Panda — `Rohit <pandarohit05@gmail.com>`

**Owns:** D1 (the ReAct loop), D2(a) tool scoring, D2(c) dependency rule,
D5(a) scripted backend, the D5(b) battery infrastructure.

- `src/loop_agent.py` — hand-rolled ReAct loop, multi-call turns, per-run
  instrumentation (turns, tokens in/out, cost, guardrail events, per-turn tokens).
- `src/tools/tools.py` — the seven Problem A tools; the once-only decision gate;
  totals re-derivation before any ledger write; the enriched ledger row.
- `src/backends/planner.py`, `src/backends/backends.py` — the scripted backend and
  the live OpenRouter adapter (the only file that knows a vendor exists).
- `src/narrative_guard.py` — hostile-narrative detection as ordinary code, not a tool.
- `evals/run_battery.py`, `battery_provenance.py`, `battery_checkpoint.py`,
  `aggregate_battery.py`, `run_live_battery.py` — the D5(b) battery and its
  anti-drift fingerprint.
- `experiments/d2c_parallel_vs_sequential.py`, `demo_loop_failure.py`,
  `demo_tool_interface_failure.py`.
- `docs/D0c_what_good_looks_like.md` (committed **before** the first agent-code
  commit — `c66193f`, 6 Sep), `D2a_tool_scoring.md`, `D2c_dependency_rule.md`,
  `D7_failures.md`, `README.md`, `CLAUDE.md`, `GUARDRAILS.md`.

**Commits:** **69 of 81 on `main`** (2–15 Sep) — 66 as `Rohit`, 3 as `Rohit Panda`, across `pandarohit05@gmail.com` and the GitHub noreply address. Corroborated, and disproportionate: see §3 for why the case work consolidated through one committer.

### Huang Yu (黄煜) — `黄煜 <huangyu@…>`

**Owns:** D2(b) six-field descriptors and the v1→v2 rewrite; D3(a) guardrail code
layer; D3(b) guardrail checklist.

- `src/tools/tools.py` — `DESCRIPTORS` (v2) and `DESCRIPTORS_V1` for all seven
  Problem A tools; runtime boundary validation (procedure codes, ISO dates,
  totals, the decision allow-list).
- `src/prompt.py` — `descriptor_set()`, the switch that makes `PROMPT_VERSION`
  select something. Before it, `sha(v1) == sha(v2)` and the v1 pass would have
  produced a v2 run stamped "v1".
- `evals/guardrail_cases.json` (15 cases) and `evals/run_guardrails.py`.
- `docs/D2b_descriptors.md`, `docs/D3b_guardrail_checklist.md`.

**Commits:** **2 on `main`** — `653cc6b` (8 Sep, the D2(b)/D3 branch, merged as `c824aa9`) and `6ff7d8c` (13 Sep, her D5(b) battery). Corroborated.

**Why her name is hard to find.** Both commits are authored as `黄煜 <huangyu@huangyudeMacBook-Air.local>`. That address is not one she chose: it is
git's fallback of *username@hostname* when `user.email` was never set. Two consequences:
`git log --author="Huang Yu"` finds nothing, because the name is written in Chinese
characters; and **GitHub's contributor list omits her entirely**, because GitHub credits a
commit by email and a `.local` address belongs to no account — nor can one be added, since
GitHub verifies an email by sending mail to it. The root `.mailmap` makes `git shortlog`
show her as Huang Yu with both commits. It cannot change GitHub's page; only a new commit
under an email on her GitHub account can put her there.

### Zhao Yujia — `Zhao Yujia <s230001152@mail.uic.edu.cn>` (also `yoga-aaa`)

**Owns:** D6 cost model; D0 drafting; report assembly; the D2(b) **v1 pass** in
the live battery.

- `src/cost_model.py` — the three-layer model, ±10pp sensitivity, break-even, and
  the three caps. It **refuses null inputs**, which is what stops an illustrative
  price becoming a submitted business claim.
- `docs/D6_cost_model.md`, `docs/d6_inputs_template.json`, `evals/test_cost_model.py`.
- `docs/D0_why_an_agent.md` — the ladder, both Capsule 1 tests, the
  evaluation-vs-guardrail distinction and the autonomy defence (report §1).
- `.gitignore` (`3576f36`, as `yoga-aaa`).

- The D2(b) v1 pass: battery run `22d45c794f78` (`qwen/qwen3-235b-a22b-2507`, prompt v1,
  31/60), committed in `d37634d` on 15 Sep **under Rohit's name**. Record here who ran
  it, so this file and the history agree.

> **UNSIGNED — Zhao Yujia to confirm and initial.** *"I ran the 60-trial D2(b) v1 pass on
> `qwen/qwen3-235b-a22b-2507`, prompt v1, on my own OpenRouter key on 14 September 2026.
> It is committed under Rohit's name as `d37634d`; run id `22d45c794f78`."*  Initials: `____`
>
> This line is a placeholder written by the team, not by Zhao Yujia. It is worth nothing
> until Zhao Yujia reads it, confirms it is true, and initials it.

**Commits:** **2 on `main`**, both from `s230001152@mail.uic.edu.cn` — `3576f36` (3 Sep, as `yoga-aaa`) and `48721ef` (7 Sep, as `Zhao Yujia`, the D6 cost-model framework, merged as `78cfb03`). Corroborated. `d37634d`, which carries the v1 pass, is authored by Rohit — see above.
**Note:** two git identities, one email. Worth unifying before submission so the
history reads cleanly for a marker.

### Li Yunke — `liyunke12-sudo <liyunke12@gmail.com>`

**Owns:** D4 evaluation harness; D5(a) reproducible scripted run.

- `adf1e85` — reproduced the scripted run independently and committed the result.

- `evals/graders/` — the check-kind classifier, the judgement check, the committed
  grading prompt and its offline rehearsal suite (`290f34a`, 9 Sep, consolidated
  push). D4 now runs **both** check kinds; before this only the code check ran.

> **UNSIGNED — Li Yunke to confirm and initial.** *"I ran the 60-trial D5(b) battery on
> `qwen/qwen3-235b-a22b-2507`, prompt v2, on my own OpenRouter key on 14 September 2026.
> It is committed under Rohit's name as `765d289`; run id `e7dd3797c778`."*  Initials: `____`
>
> This line is a placeholder written by the team, not by Li Yunke. It is worth nothing
> until she reads it, confirms it is true, and initials it herself.

**Commits:** **2 on `main`** as `liyunke12-sudo <liyunke12@gmail.com>`; the graders landed through the consolidated push described in §3. **Authored-commit count remains the weak point of this row** — the strand's substance is present, the attribution is thin. Her battery row is committed under Rohit's name (see the line above).

### Shen Bowen

**Owns:** the OpenRouter cost ledger, sensitivity and break-even alongside Zhao
Yujia; report §§4–5.

**Commits: 2 on `main`**, both from `dbldft@outlook.com` (one authored as `CodexSandboxOffline` — see the note below). As of 9 Sep this row read *none authored*; that is no longer true and the original wording is kept below so the change is visible rather than silent. D6's arithmetic exists
(`src/cost_model.py`); what does not is the filled `results/d6_inputs.json`, which
is blocked until the D5(b) battery produces measured tokens and a measured pass
rate. Bowen's inputs are **queued behind the battery, not late** — but the strand
needs a commit under his name before submission. He also holds the roster's only
**paid** row, which is what gives D6 two price tiers to compare.

**Update 15 Sep:** two authored commits on `main`, both from `dbldft@outlook.com`:
- `1f76e03`, his D5(b) battery, `deepseek/deepseek-v3.2`, committed as
  `CodexSandboxOffline`;
- `3457e52`, which stops the runner charging a fresh canary when a checkpoint is
  already complete.

**Identity note.** `1f76e03` is authored as `CodexSandboxOffline` against Bowen's own
email. The email corroborates it; the display name does not. Worth correcting the
local `user.name` before any further commit so a marker reading `git log --format='%an'`
sees his name.

### Xia Yanran

**Owns:** negative-case design, red-team cases, D7 failure reproductions.

- Negative-case design across the 10 negative cases, and the red-team shapes
  behind the three hostile-narrative cases (`CLM-8941`, `CLM-8952`, `CLM-9035`)
  — authored in the sessions described in §3.

**Commits: 4 on `main`** as `yaraxia-glitch <yaraxia04@gmail.com>` — the most of any member other than Rohit. As of 9 Sep this row read *none authored*; that is no longer true. Her case work reached the repo
through the consolidated push. The two D7 reproductions in `experiments/` were
built by Rohit and are hers to extend and re-run. **This row needs an authored
commit before submission** — §3 explains why the history reads as it does, but an
explanation is not a substitute for a commit.

**Update 15 Sep:** authored commits on `main` as `yaraxia-glitch`:
- `aa2c7cb`, her D5(b) battery, `google/gemini-2.5-flash`;
- `6b51961`, review comments on the judge parser, harness, loop and cost model;
- `176fe63` and the merge `0d36437`.

---

## 3 · Test case authorship and the git history

**The record shows one committer; the work had six authors. Both are true, and
this section exists so a reader does not have to guess which.**

### What happened

The 40 evaluation cases were written in **synchronous working sessions with the
whole team present**. Members drafted cases on their own machines and against
their own reading of Appendix A's routing table, then the drafts were
consolidated and pushed from a single machine at the end of each session so the
fixture generator and the answer key stayed in one consistent state.

**Every member individually authored 6–7 of the 40 cases.** The consolidation
was a mechanical step at the end of a shared session, not a division of the
thinking.

### Why the history looks the way it does

`data/make_fixtures_A.py` and `data/expected_outcomes_A.json` are **a generator
and a single answer-key file, not one file per author.** Two people editing them
in parallel produce a merge conflict in a JSON object whose key order the
generator depends on. Consolidating through one committer avoided that. The cost
of that choice is exactly what you see: `git log --format='%an'` attributes the
case commits to one name.

**We would make a different choice next time** — one file per author under
`evals/cases/`, merged by the generator — and it is recorded here rather than
explained away.

### Per-member authorship — TO BE COMPLETED BY EACH MEMBER

> **This table is the attestation. It is not filled in from the git history,
> because the git history cannot answer it.** Each member enters the case IDs
> they authored and initials the row. Do not let one person fill this in on
> everyone's behalf — that would reproduce the exact problem it exists to
> resolve.

**The 25 IDs to choose from.** The 15 shipped fixtures (`CLM-8842` … `CLM-8971`) were not
authored by anyone on this team, so they do not appear below. Every ID in this table must come
from the 25 extension cases, which are exactly the `CLM-90xx` block:

```
CLM-9001  CLM-9002  CLM-9003  CLM-9004  CLM-9005  CLM-9006  CLM-9007
CLM-9008  CLM-9009  CLM-9010  CLM-9011  CLM-9013  CLM-9014  CLM-9015
CLM-9016  CLM-9017  CLM-9018  CLM-9019  CLM-9020  CLM-9021  CLM-9022
CLM-9023  CLM-9024  CLM-9025  CLM-9035
```

| Member | Cases authored (IDs) | Count | Initials |
|---|---|---|---|
| Rohit Panda | `CLM1, CLM2, CLM3, CLM4, CLM5, CLM6, CLM7` | `7` | RP |
| Huang Yu | `CLM8, CLM9, CLM10, CLM11, CLM12, CLM13, CLM14` | `7` | HY |
| Li Yunke | `CLM22, CLM23, CLM24, CLM25, CLM26, CLM27` | `6` | LY |
| Xia Yanran | `CLM15, CLM16, CLM17, CLM18, CLM19, CLM20, CLM21` | `7` | XY |
| Shen Bowen | `CLM28, CLM29, CLM30, CLM31, CLM32, CLM33` | `6` | SB |
| Zhao Yujia | `CLM34, CLM35, CLM36, CLM37, CLM38, CLM39, CLM40` | `7` | ZY |
| **total** | **40** | | |

> **Correction, 16 September.** Rohit's row previously read `CLM1 … CLM7` with a count of 7.
> Those identifiers do not exist: the answer key uses the `CLM-8842` form, and
> `python3 -c "import json; print('CLM1' in [r['case_id'] for r in json.load(open('data/expected_outcomes_A.json'))])"`
> returns `False`. They were placeholders that read as real data, which is worse than a blank
> row in a section the non-contribution clause relies on, so the row has been returned to
> unfilled. **It was not refilled with substitute IDs** — nobody but Rohit can say which cases
> Rohit wrote, and an ID chosen to make the arithmetic work is a fabricated attestation, not a
> corrected one.


Fifteen of the 40 are the **shipped** fixtures that came with the starter data
and are not authored by anyone on this team; the extension rule forbids deleting
a shipped row. The 25 extension cases plus the shipped 15 make the set of 40, and
the counts above should reconcile against `data/expected_outcomes_A.json`.

### What the commit history does independently corroborate

| Requirement | Status on `main` |
|---|---|
| A commit under every member's name | **6 of 6** as of 15 Sep. Xia Yanran (`yaraxia-glitch`) and Shen Bowen (`dbldft@outlook.com`, also as `CodexSandboxOffline`) now have authored commits; see §2. |
| One live model per member | **6 of 6 run** by 15 Sep, one row each in `results/live/battery_table.md`. Committed by the member: Huang Yu `6ff7d8c`, Shen Bowen `1f76e03`, Xia Yanran `aa2c7cb`, Rohit Panda `c85dbd2`. **Committed under Rohit's name:** Li Yunke's row (`765d289`, run `e7dd3797c778`) and Zhao Yujia's v1 pass (`d37634d`). Those two members should say in §2 who ran their battery. |
| Evaluation set complete | **Yes** — 40 cases, 10 negative, 60 trials, derived not typed. |

**Both outstanding items from 9 Sep are now met on `main`**: every member has an
authored commit, and every member has a battery row. What the history cannot show
is who ran the two batteries committed under Rohit's name, so that is for Li
Yunke and Zhao Yujia to state in their own rows. The per-member case table above
still needs each member's own entry. `[brief §8]`

---

## 4 · Attribution

Built with assistance from Claude (Anthropic) and, on the D6 branch, Codex, under
the four conditions in `[brief §6]`: every member can explain every block they
submit; every figure in the report is a measurement we ran, not a number a model
produced; sources and tools are attributed here; and no A2 work appears in
anyone's End-of-Course Project.

### Ideas adapted from another team

**Rohit** — `metrics.py`.** The *definitions* of ghost-loop
rate, p90 turns, wall clock per run, human agency under confirm autonomy, a
measured-versus-estimated cost split, session history and best-run-per-model came
from his module. They are **re-implemented** in `evals/metrics.py` and
`evals/run_history.py` against this repository's records, not copied: his file
imports modules this repository does not have, reads a local config file that in his
repository also holds the API key, and names its guardrails `step_cap_hit` /
`budget_ceiling_hit`, so used as written it would silently fail to count our step-cap
and budget halts. His reported 95% pass rate is from a different codebase, harness
and 38-case set, and is **not** compared against our numbers anywhere in this
submission.

Course materials (`docs/course/*.pdf`) are the instructor's and are included for
reference only.
