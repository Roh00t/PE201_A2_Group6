# D6 — cost model, evidence and completion checklist

## Where the formula comes from

The assignment brief specifies the Class 5 three-layer model:

1. **Layer 1, variable execution cost per task**: input tokens, output tokens,
   retrieval fees and tool/API fees.
2. **Layer 2, expected failure cost per task**:
   `(1 - P) × failure_cost`, where `P` is the measured D4 success rate.
3. **Layer 3, fixed monthly cost**: monitoring, storage/infrastructure,
   evaluation and maintenance.

Therefore expected monthly cost is:

`(Layer 1 + Layer 2) × monthly volume + Layer 3`.

Appendix A fixes volume at **8,000 claims/month**. It also provides an assessor
rate of **US$38/hour** and **12 minutes** of rework for a failed task, so:

`failure_cost = 38 × (12/60) = US$7.60`.

These two numbers are official scenario inputs. They are not inferred from the
repository. By contrast, the brief supplies no universal dollar value for
Layer 3; each fixed-cost assumption must be sourced and labelled.

## Exactly what must be measured or sourced

Copy `docs/d6_inputs_template.json` to `results/d6_inputs.json` only after the
live battery, then fill:

- `cost_task_count`, `tokens_in`, `tokens_out`: from the same selected set of
  committed D5(b) records. For the assignment table, using all 60 measured
  trials is simple and conservative because negatives are deliberately
  over-weighted. For a production forecast, normalize to one run per unique
  case or a known production claim mix and state that choice;
- `success_passed`, `success_total`: `combined_trials_for_d6` from that run's
  completed D4 judgement summary, not scripted 60/60;
- token prices: the vendor's price page on the run date, also recorded in
  `evals/battery_roster.json`;
- tool/retrieval fees: zero is defensible for the repository's local JSON tools
  because they call no paid service; change it if production uses paid APIs;
- all four Layer 3 rows: a stated monthly assumption with source or calculation;
- `monthly_limit_per_user`: the third required operating cap.

Then run:

```powershell
python src/cost_model.py results/d6_inputs.json --out results/d6_summary.json
```

The program calculates each model's Layer 1 and Layer 2, the deployed monthly
total, success sensitivity at **P − 10 percentage points** and **P + 10
percentage points**, and cheap-model break-even against an expensive model:

`P_break-even = 1 - (E - C) / F`

where `C` is the cheap model's variable execution cost, `E` is the expensive
model's execution plus expected failure cost, and `F` is US$7.60.

## Where it goes in the submission

- Evidence and assumptions: `docs/D6_cost_model.md` plus source URLs/dates in
  the completed JSON.
- Reproducible arithmetic: `src/cost_model.py`.
- Filled inputs and machine output: `results/d6_inputs.json` and
  `results/d6_summary.json`.
- Report section 4: one compact three-layer table, P±10pp sensitivity, cheap vs
  expensive break-even and the three caps.
- Report section 5/demo: point to the committed inputs and rerun the one-line
  command rather than showing spreadsheet-only arithmetic.

---

## The four levers, each with a measured before and after

D6 requires all four to be named and requires us to say **which dominated our bill and
how we know.** `[brief D6]` Three of the four are measured today; the fourth is blocked
on the live battery and is marked as such rather than estimated.

| Lever | Attacks | Before | After | Measured by |
|---|---|---|---|---|
| **1 · Tool block size** | `B` — the prefix, re-sent every turn whether a tool is called or not. **Linear in `T`.** | v1 descriptors **~847 tok** (prompt 1,240) | v2 descriptors **~1,756 tok** (prompt 2,150) | `prompt.build_system_prompt("A", version=…)` |
| **2 · Turn count** | The **quadratic** term `D·T(T−1)/2`. | sequential: **357 turns**, 2,322,600 input tokens | parallel: **211 turns**, 1,091,400 input tokens — **−41% / −53%** | `experiments/d2c_parallel_vs_sequential.py` |
| **3 · Observation size** | Compounds — every observation is re-sent on every later turn. | v1 descriptors state no size bound | v2 bounds every return (`≤ 7 fields, ≤ 60 tokens`, "never a list") | `tools.DESCRIPTORS` vs `DESCRIPTORS_V1` |
| **4 · Success rate** | Sets **layer 2**, usually the largest layer. | — | **Blocked on D5(b).** Scripted 60/60 is 100% by construction and is not evidence about agent quality. | `evals/aggregate_battery.py` |

### Which dominated, and how we know

**Lever 2, by roughly six to one.**

- Lever 2 saved **20,520 input tokens per run** — (2,322,600 − 1,091,400) ÷ 60.
- Lever 1 *cost* **~910 tokens per turn** going from v1 to v2, or ~3,640 per run at our
  median of 4 turns.

So the descriptor rewrite spends about 18% of what the grouping saved. **The v2 prefix
has to earn that on every single turn of every single run**, and whether it does is a
D2(b) question the live battery answers — not something the scripted pass rate can say,
because the scripted backend never reads the prompt.

**Levers 1 and 3 look similar and are not.** A fat tool block is **linear** in `T`: pay
it once per turn. A fat observation **compounds**: it is re-sent on every later turn, so
its cost is quadratic in where it lands. That is why v2 bounds return sizes in the
descriptor text rather than only shortening the prose.

### An honest limit on lever 3

We have the v1→v2 *contract* change (no bound → an explicit bound) but **not** a
before/after measurement of bytes actually returned, because both versions call the same
functions — the bound is a promise to the model, not an enforcement in code. What the
live battery can show is whether a bounded contract changes what the model *asks for*.
Stated as a limit rather than reported as a saving.

---

## Two inputs that are easy to miss

**1 · Judge tokens are live spend outside the battery.** If D4's judgement check is run
`--by model`, that spend never passes through `run_battery` and therefore never reaches
`logs/battery/decisions__*.jsonl`. It is written to
`results/judge/judge_usage__<model>__<date>.json` instead. **Add that file as a D6 input
or the cost model under-reports actual OpenRouter billing.** The judge model must also
not be any of the five in `evals/battery_roster.json` — a model marking its own homework
is not a measurement. `[brief D4]`

**2 · Break-even is per tier, not blended.** `1 − (E − C)/F` compares **one** cheap model
against **one** expensive model. Averaging four cheap models into a single `C` produces a
break-even for a model that does not exist. Run `cheap_model`/`expensive_model` once per
pair and report the pairs, not the mean.

Why `E` folds in its own failures and `C` does not: for the expensive model we *measured*
its success rate, so we can price its failures. The cheap model's success rate is the
unknown we are solving for — it cannot appear on that side of the equation. `[brief D6]`

---

## The three caps that ship with the model

Derived from evidence, not chosen for roundness — a round number is decoration.

| Cap | Value | Where it came from |
|---|---:|---|
| Step cap | **8 turns** | Worst legitimate run is 5 (`d2c_parallel_vs_sequential.py`), plus 3 for a model that wanders once and recovers |
| Budget ceiling | **60,000 tokens/run** | Measured per-run cost; 0 of 60 trials reach it under the shipped grouping |
| Monthly limit per user | `caps.monthly_limit_per_user` | **Must be set in `results/d6_inputs.json`.** `cost_model.py` refuses to run without it |

**Make the stop loud.** A cap that silently returns an empty answer converts a visible
cost problem into an invisible correctness one — see [D7_failures.md](D7_failures.md),
where failure 2's whole point is that no cap could have detected it.
