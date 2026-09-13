# COMMANDS — the whole A2 pipeline, end to end

**PE6201 A2 · Problem A · Group 6** · last verified **9 September 2026**

Python 3.9+. **Standard library only** — nothing to install.
Everything except §5 is **free, offline and deterministic**. Only §5 spends money.

---

## 1 · Configuration checks — free, no key

```bash
python3 evals/check_roster_prices.py
```

Public `GET /models`. Confirms every roster model **still exists**, re-prices the
battery on our own measured tokens, and re-derives each tier from that cost. Run
it **on the day**, before anyone spends — `validate_roster()` refuses a
`price_checked_on` older than 14 days.

> Two model ids we were given earlier did not exist on OpenRouter, and three
> supplied prices were wrong. Either bad id raises `LiveFatalError` on the first
> call of a run — after the key is entered. This check is why that never happened.

```bash
python3 evals/check_roster_prices.py --update
```

Rewrites prices, tiers and dates **only when you have read the diff**. A model
that changed price band may no longer belong to the member holding it.

```bash
python3 data/check_my_data.py
```

Fixtures hang together; every case a label refers to exists.

```bash
python3 run_eval.py --prompt
```

The exact system prompt a live model receives, with its token cost. Re-run this
after any descriptor change — it is the D2(b) artefact.

---

## 2 · Code and guardrail checks — free, no key

```bash
python3 evals/test_battery_fake.py         # 60 checks · battery failure modes
python3 evals/graders/test_judge_fake.py   # 51 checks · judge failure modes
python3 evals/test_cost_model.py           #  4 checks · D6 arithmetic
python3 evals/run_guardrails.py --twice    # D3(b) · 15 guardrail cases
python3 evals/graders/code_check.py        # D4 · which check grades which case
```

`--twice` on the guardrails proves the run is **deterministic**; a checklist that
gives two answers is not a checklist.

The two `test_*_fake.py` suites rehearse every failure mode **before any of them
costs money** — including the two that would silently inflate a pass rate: a
malformed judge reply counted as a pass, and a skipped case shrinking the
denominator.

---

## 3 · The scripted baseline — D5(a), D2(c), D7. Free, no key

```bash
python3 run_eval.py                                    # 60 of 60 trials
python3 run_eval.py CLM-8842                           # one case, every turn
python3 experiments/d2c_parallel_vs_sequential.py      # D2(c), both groupings
python3 experiments/demo_loop_failure.py               # D7 failure 1 · loop control
python3 experiments/demo_tool_interface_failure.py     # D7 failure 2 · tool interface
```

`BACKEND = "scripted"` is the committed default, so a clean clone reproduces
**60/60 with no key**. Technical Execution is capped if that stops being true.

**Reset the ledger before you commit it.** `logs/decisions.jsonl` is append-only,
so a dev session leaves hundreds of rows. The submitted artefact is one clean
pass — 30 rows, one per approved claim:

```bash
rm -f logs/decisions.jsonl && python3 run_eval.py
```

---

## 4 · The judgement and grading pass — D4's second check

```bash
# free — a person rules on each required item
python3 evals/graders/judge.py results/scripted/problemA__scripted__v2__<date>.json --by person

# a second model (mistralai/mistral-small-2603), ~US$0.013 for all 40 cases
OPENROUTER_API_KEY=sk-or-... \
python3 evals/graders/judge.py results/scripted/problemA__scripted__v2__<date>.json \
  --by model --limit 3          # verify the wiring on 3 cases FIRST
```

Writes `<input>__judged.json` — **never overwrites the input**, so judging can be
re-run, compared or thrown away.

**Three refusals you cannot switch off:**

| Refusal | Why |
|---|---|
| The judge may not be the model being graded, or any model on the roster | *"Use a different model from the one being graded."* A model marking its own homework is not a measurement |
| A malformed reply is a **FAIL**, never a pass | Counting an unparseable answer as a pass inflates the rate — the one direction a harness must never round |
| `PENDING` items are excluded from **both** numerator and denominator | An unjudged item may not quietly move a percentage |

Judge spend is written to `results/judge/judge_usage__*.json` with **measured**
tokens. **This is a D6 input** — it never passes through `run_battery`, so it
never reaches `logs/battery/`, and a cost model that omits it under-reports the
real OpenRouter bill.

---

## 5 · The live multi-model battery — D5(b). **THE ONLY PART THAT SPENDS MONEY**

### Every member runs exactly one command

```bash
python3 run_live_battery.py --name "Zhao Yujia"
```

Your name in any form — `"Zhao Yujia"`, `zhao_yujia`, `yujia`, or 赵宇佳. Run it
with no `--name` and it lists the roster and asks.

### Rehearse first. It costs nothing and exercises the whole path

```bash
python3 run_live_battery.py --name "Zhao Yujia" --dry-run
```

### What happens, in order

1. **Your model is already chosen.** Read from `evals/battery_roster.json` — you
   do not pick one, and you cannot run someone else's.
2. **The run is priced against measured tokens** from the committed scripted run
   (18,190 in / 542 out per trial), with a **×3 safety factor on output** because
   a scripted transcript is a *floor* on what a live model writes.
3. **It refuses to start over US$3.** Not a warning — a refusal, with the brief's
   own remedy printed.
4. **You confirm by typing the model id back.** Anything else aborts and spends
   nothing.
5. **Your key is asked for last**, hidden as you type. It is held in one variable
   in memory: never written to a file, never put in `os.environ`, never in a
   results file, and scrubbed from any traceback.
6. **A canary runs on three case shapes** before committing to all 60 trials.
7. **The battery runs**, checkpointed to disk after every trial and halting on
   **measured** cost — not on the estimate.
8. **Results are written twice**: the canonical
   `results/live/battery__*.json` that `aggregate_battery.py` reads, and your own
   copy at `results/live/<member>/problemA__live_<member>_<model>_<date>.json`.
   **Keep both** — deleting the canonical one empties the D5(b) table.

### Chaining the judgement check

```bash
python3 run_live_battery.py --name "Zhao Yujia" --judge
```

Judging is a **second, separately confirmed, separately capped** live spend on a
different model. It is deliberately *not* folded into the battery's price,
because the estimate you approved priced the battery alone — chaining it silently
would make the number you consented to wrong. You type `judge` to proceed.

### If something goes wrong

| Situation | What to do |
|---|---|
| Laptop closed, connection dropped | Re-run the same command. The checkpoint resumes and **does not re-pay** for completed trials |
| `429` / rate limit | Nothing. `LIVE_CALL` retries with backoff, honouring `Retry-After`. It costs time, not money |
| `401` / `402` / `404` | Aborts immediately with a plain message. **No retry loop against a dead key or a typo'd model id** |
| "worktree is DIRTY" | Commit or stash. Six people running from six different working trees is drift, and drift silently voids the whole battery |
| A run looks wrong | `python3 run_battery.py --member <you> --verify-drift` and paste it in the group chat. All six blocks must be identical |

### Before anyone spends — in this order, no exceptions

```bash
python3 evals/check_roster_prices.py        # 1 · ids and prices, on the day
python3 run_battery.py --freeze             # 2 · ONCE, stamps the fingerprint hashes
git add evals/battery_roster.json && git commit -m "chore(d5b): freeze the battery"
git tag v2-freeze && git push origin main --tags        # 3 · cut the tag
```

**Nobody merges to `main` until every result is in.** Member 1 runs alone first;
everyone reads that file before the other five follow.

### After everyone has run

```bash
python3 evals/aggregate_battery.py          # the D5(b) table + the v1→v2 delta
```

Refuses to present a comparison across drifted runs, and **names the component
that moved**. It reports two negative numbers, not one: the negative *trial* rate
and the negative *3-of-3* rate. A model at 90% trial / 70% three-of-three is
unreliable on refusals; one at 90%/90% is consistently wrong about one case.

---

## 6 · This run's roster — N−1 models

Six members, **five distinct models**. The sixth runs the D2(b) v1 pass on a model
already in the battery, because comparing prompt versions means holding the model
fixed.

| Member | Model | Family | Tier | Prompt | Battery |
|---|---|---|---|---|---:|
| Rohit Panda | `anthropic/claude-haiku-4.5` | anthropic | mid | v2 | $1.5792 |
| Huang Yu | `openai/gpt-4.1-mini` | openai | mid | v2 | $0.5927 |
| Xia Yanran | `google/gemini-2.5-flash` | google | mid | v2 | $0.5713 |
| Li Yunke | `qwen/qwen3-235b-a22b-2507` | qwen | cheap | v2 | $0.1296 |
| Shen Bowen | `deepseek/deepseek-v3.2` | deepseek | cheap | v2 | $0.3326 |
| Zhao Yujia | `qwen/qwen3-235b-a22b-2507` | qwen | cheap | **v1** | $0.1296 |
| | | | | **total** | **$3.3351** |

**3 mid · 2 cheap · 5 distinct families.** Both of the brief's conditions hold and
both are checked in `validate_roster()`, not left to memory: the v2 set spans two
price tiers, and no two v2 members share a family. Zhao Yujia's family duplicating
Li Yunke's is correct — the family rule applies to the five **v2** models.

Worst individual row is **$1.5792** (Haiku 4.5), 53% of the US$3 ceiling. The whole
battery is about **6%** of the team's six US$10 keys. Updated 2026-09-13.

**Priced on 60 trials, not 56.** The brief's example set is 40 cases / 8 negative /
56 trials; ours is 40 / 10 / 60, because nine of the fifteen *shipped* cases are
already negative and a shipped row may not be deleted. `plan_shape()` derives it;
`run_battery` refuses to start if a typed number disagrees.

**The judge is not on this roster and must never be.** `judge.py` defaults to
`mistralai/mistral-small-2603` — Mistral is deliberately absent above, and
`test_judge_fake.py` re-checks that against the live roster on every run.

---

## 7 · Commands that do NOT do what they look like

| Looks right | Actually |
|---|---|
| `run_eval.py --model scripted` | `scripted` is parsed as a **case id**, matches no label, and **nothing runs**. Scripted is already the default — use bare `python3 run_eval.py` |
| `pytest` | There is no pytest and no dependency to install. The suites are the `test_*.py` files in §2, run directly |
| Deleting `results/live/battery__*.json` after copying it | Empties the D5(b) table. `aggregate_battery.py` reads the canonical name |
| Editing a number in a results file | Voids the run. Re-run instead — that is what the checkpoint is for |
