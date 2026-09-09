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
- `docs/D0_why_an_agent.md` — the ladder, both Capsule 1 tests, the
  evaluation-vs-guardrail distinction and the autonomy defence (report §1).
- `.gitignore` (`3576f36`, as `yoga-aaa`).

**Commits:** `48721ef` (7 Sep), `3576f36` (3 Sep), merged as `78cfb03`. Corroborated.
**Note:** two git identities, one email. Worth unifying before submission so the
history reads cleanly for a marker.

### Li Yunke — `liyunke12-sudo <liyunke12@gmail.com>`

**Owns:** D4 evaluation harness; D5(a) reproducible scripted run.

- `adf1e85` — reproduced the scripted run independently and committed the result.

- `evals/graders/` — the check-kind classifier, the judgement check, the committed
  grading prompt and its offline rehearsal suite (`290f34a`, 9 Sep, consolidated
  push). D4 now runs **both** check kinds; before this only the code check ran.

**Commits:** 1 authored (`adf1e85`, 8 Sep); the graders landed through the
consolidated push described in §3. **Authored-commit count is the weak point of
this row** — the strand's substance is present, the attribution is thin.

### Shen Bowen

**Owns:** the OpenRouter cost ledger, sensitivity and break-even alongside Zhao
Yujia; report §§4–5.

**Commits: none authored on `main` as of 9 Sep.** D6's arithmetic exists
(`src/cost_model.py`); what does not is the filled `results/d6_inputs.json`, which
is blocked until the D5(b) battery produces measured tokens and a measured pass
rate. Bowen's inputs are **queued behind the battery, not late** — but the strand
needs a commit under his name before submission. He also holds the roster's only
**paid** row, which is what gives D6 two price tiers to compare.

### Xia Yanran

**Owns:** negative-case design, red-team cases, D7 failure reproductions.

- Negative-case design across the 10 negative cases, and the red-team shapes
  behind the three hostile-narrative cases (`CLM-8941`, `CLM-8952`, `CLM-9035`)
  — authored in the sessions described in §3.

**Commits: none authored on `main` as of 9 Sep.** Her case work reached the repo
through the consolidated push. The two D7 reproductions in `experiments/` were
built by Rohit and are hers to extend and re-run. **This row needs an authored
commit before submission** — §3 explains why the history reads as it does, but an
explanation is not a substitute for a commit.

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

| Member | Cases authored (IDs) | Count | Initials |
|---|---|---:|---|
| Rohit Panda | `CLM1, CLM2, CLM3, CLM4, CLM5, CLM6, CLM7` | `7` | RP |
| Huang Yu | `<CLM-…, CLM-…>` | | |
| Li Yunke | `<CLM-…, CLM-…>` | | |
| Xia Yanran | `<CLM-…, CLM-…>` | | |
| Shen Bowen | `<CLM-…, CLM-…>` | | |
| Zhao Yujia | `<CLM-…, CLM-…>` | | |
| | **total** | **40** | |

Fifteen of the 40 are the **shipped** fixtures that came with the starter data
and are not authored by anyone on this team; the extension rule forbids deleting
a shipped row. The 25 extension cases plus the shipped 15 make the set of 40, and
the counts above should reconcile against `data/expected_outcomes_A.json`.

### What the commit history does independently corroborate

| Requirement | Status on `main` |
|---|---|
| A commit under every member's name | **4 of 6.** Huang Yu, Li Yunke, Zhao Yujia and Rohit Panda have authored commits. Xia Yanran and Shen Bowen do not yet. |
| One live model per member | **0 of 6 run.** The roster is filled, live-verified and validated (5 free + 1 paid, ≈US$0.06 total); `v2-freeze` is not yet cut. |
| Evaluation set complete | **Yes** — 40 cases, 10 negative, 60 trials, derived not typed. |

**The two outstanding items are both fixable before submission and neither is a
matter of wording.** Xia Yanran and Shen Bowen each need at least one authored
commit, and all six members need to run their own battery under their own key —
which is the other row the declaration marks NOT OPTIONAL. `[brief §8]`

---

## 4 · Attribution

Built with assistance from Claude (Anthropic) and, on the D6 branch, Codex, under
the four conditions in `[brief §6]`: every member can explain every block they
submit; every figure in the report is a measurement we ran, not a number a model
produced; sources and tools are attributed here; and no A2 work appears in
anyone's End-of-Course Project.

Course materials (`docs/course/*.pdf`) are the instructor's and are included for
reference only.
