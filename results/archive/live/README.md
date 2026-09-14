# Superseded battery runs — kept as evidence, excluded from the table

`aggregate_battery.py` reads `results/live/battery__*.json` only, so nothing here
reaches the D5(b) table or the v1→v2 delta. `experiments/regrade_offline.py` and
`experiments/provider_audit.py` read both directories.

## Harness defects — rohit_panda, 2026-09-12 to 13

These ran against a loop that did **not** replay the model's own tool calls
into the transcript (`src/loop_agent.py`, fixed in `874e933`). The model could
not see what it had already called, re-issued it, and our de-duplication guard
killed the run.

They are **not** comparable with anything produced after that commit, and
`aggregate_battery.py` must never pick them up — hence this directory sits
*parallel* to `results/live/`, not inside it.

| File | What it measured |
|---|---|
| `battery__rohit_panda__…__2026-09-12__83bdbe168d2a.json` | Strict JSON parser **and** transcript amnesia. 0/60; 38 trials unparseable. |
| `battery__rohit_panda__…__2026-09-13__b4944646db6d.json` | Tolerant parser, transcript amnesia remaining. 1/60; **48 of 60 halted on `duplicate_action`**, 7 unparseable, 5 completed. |
| `battery__rohit_panda__…__2026-09-13__7462a14e17e9.json` | The `--limit 5` gate after the transcript fix. **0 `duplicate_action` halts** — the fix worked — but **7 of 7 unparseable**. Still on two further defects found afterwards: the parser broke on replies holding two JSON objects, and **the model was never told which claim it was deciding** (`a4043b5`). |
| `battery__rohit_panda__anthropic-claude-haiku-4.5__…__837857b1f026.json` | **The first run on the fixed harness, and it passed as a harness test**: 0 unparseable, 0 `duplicate_action`, median 5 turns, canary cost on estimate, 4/4 approvals correct. It failed a **prompt** test instead: on `CLM-8888` Haiku 4.5 found the missing pre-authorisation, named line 62480 and date 2026-09-08, returned `request_document` — and then called `issue_decision_letter` anyway, 3/3 trials. v2's process section said *"call issue_decision_letter, then finish"* without a condition, and the tool's signature lists all three outcomes. A model that follows instructions exactly is the one that exposes an imprecise instruction. A genuine **prompt-layer** failure — fixed in the commit that archived this file. |

The second is the one worth citing in D7: it is a clean demonstration that a
pass rate can be dominated by a defect in the harness rather than by the model
under test, and that a 100% scripted run cannot detect it — `ScriptedBackend`
ignores the transcript by design.

Inspect either with:

```bash
python3 evals/metrics.py results/archive/live/<file>.json
```

## Provider fault — li_yunke, `qwen/qwen3-235b-a22b-2507`, v2, 2026-09-14

Two complete batteries on one day, with the same answer key (`1cd26cc1bf91`),
plan (`5952ce9e5763`) and v2 prompt (`60c5e4344f24`). OpenRouter sent each call
to one of ten providers. **DeepInfra answered 28 of its 42 calls with text that
is not an action:** a blank line after every word (`"an\n\nerror"`,
`"a\n\nnew\n\nline"`), even inside JSON, or a single token. The other nine
providers answered 412 calls and none was unparseable.

| Run | Commit | Recorded | DeepInfra calls · unparseable | Trials that reached DeepInfra | Trials that never did |
|---|---|---|---|---|---|
| `battery__li_yunke__…__e7dd3797c778.json` | `ecc3ab5` | 41/60 (68.3%) | 19 · 12 | 2/18 passed | 39/42 passed |
| `battery__li_yunke__…__6dfb98e18210.json` | `7bfa43d` | 37/60 (61.7%) | 23 · 16 | 3/21 passed | 34/39 passed |

The gap between two identical runs is routing, not the model or the prompt. It
would also drown D2(b): Zhao Yujia's v1 pass runs on this model, and a v1→v2
difference cannot be read against a four-trial swing between two v2 runs. The
trials that never reached DeepInfra passed 73 of 81 (90.1%); they were selected
after the fact, so that is a diagnostic, not a pass rate.

**Declared before the replacement run.** From 2026-09-14, every battery still to
run (li_yunke's third run, zhao_yujia, shen_bowen, xia_yanran) uses an
OpenRouter account with **DeepInfra in Ignored Providers**
(openrouter.ai/settings/privacy), and li_yunke's third run takes her row in the
D5(b) table. The evidence is on this model only; for the other models it is a
precaution that keeps every remaining run on the same routing rule. Each call's
provider is in the record, so the rule is checked, not assumed:

```bash
python3 experiments/provider_audit.py
```

**Judgement check.** `e7dd3797c778` has 18 of 40 cases judged: it was resumed
before `57121af`, when a resumed battery queued only the cases that ran after
the resume. `6dfb98e18210` has all 40, and 18 pass as written but **17** is
correct. Its CLM-8941 record is an unparseable reply (1 output token). The judge
marked both required items "present", citing "model did not return parseable
JSON" as the evidence, while its own reason says both were absent;
`parse_verdict` counts the per-item verdicts. The judged file is left as the
judge wrote it.

**The rest of each run stays where its records point.** Member copies and
judged files: `results/live/li_yunke/`. Ledgers: `logs/battery/`. Checkpoints:
`results/live/checkpoints/`. Judge spend, both D6 inputs:
`results/judge/judge_usage__mistralai-mistral-small-2603__li_yunke__qwen-qwen3-235b-a22b-2507__2026-09-14__e7dd3797c778.json`
(US$0.0077) and `…__6dfb98e18210.json` (US$0.0162).
