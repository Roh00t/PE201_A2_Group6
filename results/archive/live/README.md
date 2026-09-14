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

Three complete batteries on one day, with the same answer key (`1cd26cc1bf91`),
plan (`5952ce9e5763`) and v2 prompt (`60c5e4344f24`). OpenRouter sent each call
to one of ten providers. **DeepInfra answered 33 of its 50 calls with text that
is not an action:** a blank line after every word (`"an\n\nerror"`,
`"a\n\nnew\n\nline"`), even inside JSON, or a single token. The other nine
providers answered 661 calls and none was unparseable.

| Run | Where | Commit | Recorded | DeepInfra calls · unparseable | Trials that reached DeepInfra | Trials that never did | Battery US$ |
|---|---|---|---|---|---|---|---|
| `battery__li_yunke__…__e7dd3797c778.json` | `results/live/` — **her row** | `ecc3ab5` | 41/60 (68.3%) | 19 · 12 | 2/18 passed | 39/42 passed | 0.0858 |
| `battery__li_yunke__…__6dfb98e18210.json` | here | `7bfa43d` | 37/60 (61.7%) | 23 · 16 | 3/21 passed | 34/39 passed | 0.0803 |
| `battery__li_yunke__…__ecb1ca22c1c3.json` | here | `0e1a590` | 49/60 (81.7%) | 8 · 5 | 2/7 passed | 47/53 passed | 0.0951 |

**What happened, in order.**

1. After runs 1 and 2, `0e1a590` (19:50) declared that every battery still to
   run would use an OpenRouter account with DeepInfra in Ignored Providers, and
   that li_yunke's third run would take her row.
2. Run 3 (19:53–20:17) ran on an account with that setting, and DeepInfra still
   answered 8 calls in 7 trials, spread from 19:56 to 20:13.
   `python3 experiments/provider_audit.py` failed it. The records cannot show
   whether the setting was missing from the account behind that key or was not
   applied.
3. **Decision, after run 3: stop re-running.** Her row is her first complete
   run, `e7dd3797c778`, chosen by a rule that does not look at scores. Runs 2
   and 3 are replications. **The DeepInfra rule is withdrawn**, so zhao_yujia's
   v1 pass ran on default routing, as her row did: 14 of its trials reached
   DeepInfra, and 2 of those 20 replies were unparseable.

**How to read her row.**

- Identical v2 runs scored 37–49/60, and the score falls as DeepInfra exposure
  rises: 18 trials reached it and the run scored 41, 21 scored 37, and 7
  scored 49.
- Read the v1→v2 difference (zhao_yujia 31/60) against that spread.
- Trials never routed to DeepInfra passed 120/134 (89.6%) on v2 and 23/46 (50%)
  on v1. Those trials were selected after the fact, so these are diagnostics,
  not pass rates.
- DeepInfra's junk rate was 66% on v2's 3,134-token first prompt and 10% on v1's
  1,106-token one, so the fault costs v2 more than v1.

**Judgement check.**

- `e7dd3797c778` has 18 of 40 cases judged. It was resumed before `57121af`,
  when a resumed battery queued only the cases that ran after the resume.
  `python3 experiments/complete_judgement.py --member li_yunke` judges the other
  22 and keeps the 18.
- `6dfb98e18210` has all 40 judged. 18 pass as written, but **17** is correct.
  Its CLM-8941 record is an unparseable reply (1 output token). The judge marked
  both required items "present", citing "model did not return parseable JSON"
  as the evidence, while its own reason says both were absent, and
  `parse_verdict` counts the per-item verdicts. The judged file is left as the
  judge wrote it.
- `ecb1ca22c1c3` has all 40 judged, 26 pass, and none of those passes is on one
  of its five unparseable records.

**The rest of each run stays where its records point.**

- Member copies and judged files: `results/live/li_yunke/`.
- Ledgers: `logs/battery/`.
- Checkpoints: `results/live/checkpoints/`.
- Judge spend, all D6 inputs, in `results/judge/`:
  `judge_usage__mistralai-mistral-small-2603__li_yunke__qwen-qwen3-235b-a22b-2507__2026-09-14__<run id>.json`,
  at US$0.0077 (`e7dd3797c778`), US$0.0162 (`6dfb98e18210`) and US$0.0165
  (`ecb1ca22c1c3`). Finishing run 1 adds `…__e7dd3797c778__pass2.json`.
