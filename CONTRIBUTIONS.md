# CONTRIBUTIONS

**PE6201 A2 · Applied AI System · Problem A — health-insurance claim first response**
Team ID: `<FILL>` · Section: `<FILL>` · Last updated: **9 September 2026**

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

**Commits:** 17 on `main` (2–9 Sep). Corroborated.

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

**Commits:** `653cc6b` (8 Sep), merged as `c824aa9`. Corroborated.

### Zhao Yujia — `Zhao Yujia <s230001152@mail.uic.edu.cn>` (also `yoga-aaa`)

**Owns:** D6 cost model; D0 drafting; report assembly; the D2(b) **v1 pass** in
the live battery.

- `src/cost_model.py` — the three-layer model, ±10pp sensitivity, break-even, and
  the three caps. It **refuses null inputs**, which is what stops an illustrative
  price becoming a submitted business claim.
- `docs/D6_cost_model.md`, `docs/d6_inputs_template.json`, `evals/test_cost_model.py`.
- `.gitignore` (`3576f36`, as `yoga-aaa`).

**Commits:** `48721ef` (7 Sep), `3576f36` (3 Sep), merged as `78cfb03`. Corroborated.
**Note:** two git identities, one email. Worth unifying before submission so the
history reads cleanly for a marker.

### Li Yunke — `liyunke12-sudo <liyunke12@gmail.com>`

**Owns:** D4 evaluation harness; D5(a) reproducible scripted run.

- `adf1e85` — reproduced the scripted run independently and committed the result.

**Commits:** 1 (8 Sep). **Under-corroborated against the strand.**
`evals/harness.py` is currently Rohit's. Yunke's outstanding work is the part of
D4 that does not yet exist: `evals/graders/code_check.py` (the per-case
code-vs-judgement classifier), `evals/graders/judge.py` and its committed
`judge_prompt.md`, and the per-case results table. `evals/graders/` is three empty
files today. **D4 requires both check kinds; only the code check runs.**

### Shen Bowen

**Owns:** the OpenRouter cost ledger, sensitivity and break-even alongside Zhao
Yujia; report §§4–5.

**Commits: none on `main` as of 9 Sep.** D6's arithmetic exists
(`src/cost_model.py`); what does not exist is the filled `results/d6_inputs.json`,
which is blocked until the D5(b) battery produces measured tokens and a measured
pass rate. Bowen's inputs are therefore **queued behind the battery, not late** —
but the strand needs a commit under his name before submission.

### Xia Yanran

**Owns:** negative-case design, red-team cases, D7 failure reproductions.

**Commits: none on `main` as of 9 Sep.** The two D7 reproductions currently in
`experiments/` were written by Rohit and are ready to be taken over, extended and
re-run. The 10 negative cases in the set were written by Rohit as well.

---

## 3 · The gap this file exists to make visible

Two rows of the Team Declaration are marked **not optional**: *everyone writes
evaluation cases*, and *everyone runs one live model*. `[brief §8]`

**Neither is satisfied yet.**

| Requirement | Status |
|---|---|
| 40 evaluation cases, 5–8 authored per member | **25 of 40 extension cases are under one git identity.** The remaining 15 are the shipped fixtures. A set written by one head tests one head's assumptions. `[faq]` |
| One live model per member (5 models + 1 v1 pass) | **0 of 6 run.** `evals/battery_roster.json` is still placeholders; `v2-freeze` has not been cut. |
| A commit under every member's name | **4 of 6.** Missing: Xia Yanran, Shen Bowen. |

This is a process finding, not an accusation — the work was front-loaded onto one
branch to unblock everyone else, and three of the six strands landed in the last
48 hours. But the declaration is checked against the history, so the fix is
commits, not prose: **each member authoring their own cases in
`eval/cases/<name>.json` and running their own battery under their own key.**

---

## 4 · Attribution

Built with assistance from Claude (Anthropic) and, on the D6 branch, Codex, under
the four conditions in `[brief §6]`: every member can explain every block they
submit; every figure in the report is a measurement we ran, not a number a model
produced; sources and tools are attributed here; and no A2 work appears in
anyone's End-of-Course Project.

Course materials (`docs/course/*.pdf`) are the instructor's and are included for
reference only.
