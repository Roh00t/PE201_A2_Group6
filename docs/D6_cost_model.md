# D6 — cost model, evidence and completion checklist

## Filled · 15 September 2026

**Inputs:** [`results/d6_inputs.json`](../results/d6_inputs.json). **Output:**
[`results/d6_summary.json`](../results/d6_summary.json). Reproduce with:

```bash
python3 src/cost_model.py results/d6_inputs.json --out results/d6_summary.json
```

### What went in, and the choices behind it

- **One v2 battery per model**: five models, 60 trials over 40 cases each. Tokens
  are measured, and each price is the one fetched from OpenRouter on that run's day.
- **Success rate** is the D4 code check over all 60 trials, exactly as in
  `results/live/battery_table.md`. The set over-weights negative cases (30 of 60
  trials), so this is conservative for a real claim mix. The judgement check
  grades how the record is worded, not the decision a person would redo, so it is
  reported but does not set layer 2.
- **List price is the baseline.** OpenRouter billed less where a provider cached the
  prompt; that is reported below, not built in. `[brief D6]`
- **Excluded:** zhao_yujia's v1 pass, which compares prompts rather than deployment
  candidates, and the archived runs.

### Result

| Model | Success (60 trials) | Layer 1 / task | Layer 2 / task | All-in / task | Monthly at 8,000 |
|---|---:|---:|---:|---:|---:|
| **`anthropic/claude-haiku-4.5`** (deployed) | **54/60 (90.0%)** | US$0.0211 | US$0.7600 | **US$0.7811** | **US$6,731** |
| `openai/gpt-4.1-mini` | 48/60 (80.0%) | US$0.0077 | US$1.5200 | US$1.5277 | US$12,703 |
| `deepseek/deepseek-v3.2` | 48/60 (80.0%) | US$0.0048 | US$1.5200 | US$1.5248 | US$12,680 |
| `google/gemini-2.5-flash` | 44/60 (73.3%) | US$0.0058 | US$2.0267 | US$2.0325 | US$16,741 |
| `qwen/qwen3-235b-a22b-2507` | 41/60 (68.3%) | US$0.0014 | US$2.4067 | US$2.4081 | US$19,746 |

Monthly figures include layer 3, US$481.57. For comparison, a person handling all
8,000 claims at the brief's 12 minutes and US$38/h costs **US$60,800 a month**.

**Layer 2 is 90% of the deployed bill.** US$6,080 of US$6,731 is the expected cost of
failures, and on a per-task basis failure is 97% of Haiku's cost. Every model is
priced mostly by how often it is wrong, not by its tokens.

### Sensitivity · deployed model, success ±10 percentage points

| Success | Monthly |
|---:|---:|
| 80% (−10pp) | US$12,811 |
| **90% (measured)** | **US$6,731** |
| 100% (+10pp) | US$651 |

**The case against doing it by hand survives the whole range.** Even at −10pp the
agent costs a fifth of the all-human US$60,800.

**The choice of Haiku does not survive it.** At 80%, Haiku costs US$107–131 a
month more than gpt-4.1-mini or deepseek-v3.2 at their measured 80%. When success
is equal, cheaper tokens win. Haiku is the right deployment only while it really
succeeds more often than the others. On this set its margin is 6 trials in 60,
from one run each.

### Break-even · each cheaper model against Haiku 4.5

`P = 1 − (E − C)/F`, with `E` = Haiku's all-in US$0.7811 and `F` = US$7.60. The
pairs are run one at a time, never blended.

| Cheaper model | C (layer 1) | Break-even success | Measured | Clears it? |
|---|---:|---:|---:|---|
| `deepseek/deepseek-v3.2` (cheap) | US$0.0048 | **89.78%** | 80.0% | No, 9.8pp short |
| `qwen/qwen3-235b-a22b-2507` (cheap) | US$0.0014 | 89.74% | 68.3% | No |
| `openai/gpt-4.1-mini` (mid) | US$0.0077 | 89.82% | 80.0% | No |
| `google/gemini-2.5-flash` (mid) | US$0.0058 | 89.80% | 73.3% | No |

Because `C` is tiny next to `F`, every break-even sits within 0.3pp of Haiku's own
90%. **A cheaper model has to match the expensive one's success rate almost
exactly; its token price barely matters.** Reproduce the pairs:

```bash
python3 - <<'PY'
import json, sys; sys.path.insert(0, "src")
from cost_model import calculate
doc = json.load(open("results/d6_inputs.json"))
for cheap in doc["models"]:
    if cheap != doc["expensive_model"]:
        b = calculate(dict(doc, cheap_model=cheap))["cheap_model_break_even"]
        print(cheap, "%.2f%%" % (100 * b["required_cheap_success_rate_raw"]))
PY
```

### Layer 3 · stated monthly assumptions

| Row | Monthly | Basis |
|---|---:|---|
| Monitoring | US$152.00 | Assumption: 4 h/month reading the decision ledger and every cap, halt and override event, at the brief's only labour rate, US$38/h |
| Storage and infrastructure | US$20.00 | Assumption, not checked against a vendor price list: one small host. The ledger grows about 8 MB a month |
| Evaluation | US$5.57 | Calculation: Haiku's measured battery (US$1.2682) plus judge pass (US$0.0173), re-run weekly |
| Maintenance | US$304.00 | Assumption: 8 h/month of descriptor, fixture, answer-key and price upkeep at US$38/h |
| **Total** | **US$481.57** | 7% of the deployed bill. Doubling it changes no conclusion above |

### Caching · billed against list

| Run | List (the baseline) | Billed by OpenRouter |
|---|---:|---:|
| gpt-4.1-mini | US$0.4634 | US$0.1920, with 90% of input tokens cached |
| deepseek-v3.2 | US$0.2853 | US$0.1260 |
| gemini-2.5-flash | US$0.3476 | US$0.2218 |
| qwen3-235b (v2, her row) | US$0.0858 | US$0.0696 |
| claude-haiku-4.5 | US$1.2682 | US$1.2682, no caching applied |

Caching lowers layer 1, and layer 1 is under 3% of every model's all-in cost, so
it changes no ranking. The measured figure is kept beside the baseline, as the
brief asks.

### What the project actually spent

Twelve live batteries, archived and replication runs included: **US$2.89 at list
price, US$2.24 billed**. Judging added **US$0.144**, and canary runs are not in
either figure. The five deployment rows above account for US$2.45 of the list
total.

---

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

*Written before the battery, as a checklist. When the inputs were filled on 15 September,
success was taken from the code check rather than a combined judgement figure; the reason
is under "What went in" above.*

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
| **1 · Tool block size** | `B` — the prefix, re-sent every turn whether a tool is called or not. **Linear in `T`.** | v1 descriptors **~847 tok**; live first prompt **1,106 tok** | v2 descriptors **~1,756 tok**; live first prompt **3,134 tok**; input per trial on qwen3-235b 6,126 → 14,440 | `prompt.build_system_prompt`; the qwen3-235b batteries' `turn_usage` |
| **2 · Turn count** | The **quadratic** term `D·T(T−1)/2`. | sequential: **357 turns**, 2,322,600 input tokens | parallel: **211 turns**, 1,091,400 input tokens — **−41% / −53%** | `experiments/d2c_parallel_vs_sequential.py` |
| **3 · Observation size** | Compounds — every observation is re-sent on every later turn. | v1 descriptors state no size bound | v2 bounds every return (`≤ 7 fields, ≤ 60 tokens`, "never a list") | `tools.DESCRIPTORS` vs `DESCRIPTORS_V1` |
| **4 · Success rate** | Sets **layer 2**, usually the largest layer. | qwen3-235b on v1: 31/60, layer 2 **US$3.67**/task | on v2: 41/60, layer 2 **US$2.41**/task; across models 68.3%–90.0% | `evals/aggregate_battery.py`, `results/d6_summary.json` |

### Which dominated, and how we know

**Lever 4, by more than an order of magnitude.** Now that the battery has run,
layer 2 is 97% of the deployed model's per-task cost.

The clearest measurement is the v1 → v2 rewrite on qwen3-235b:
- **What it cost (lever 1):** US$0.00075 a task, from more than double the input
  tokens per trial.
- **What it saved (lever 4):** US$1.27 a task in expected failures, as success went
  51.7% → 68.3%. That is about US$10,100 a month at 8,000 claims.

A bigger prompt that raises success is the cheapest money in the model.

**Inside layer 1, lever 2 dominates.** Grouping saved 20,520 input tokens a trial,
while v2's whole prompt growth, measured live on qwen3-235b, added 8,313: about two and
a half to one. The two counts come from different tokenisers. The comparison below was
written before the battery, against descriptor tokens alone:

- Lever 2 saved **20,520 input tokens per run** — (2,322,600 − 1,091,400) ÷ 60.
- Lever 1 *cost* **~910 tokens per turn** going from v1 to v2, or ~3,640 per run at our
  median of 4 turns.

So the descriptor rewrite spends about 18% of what the grouping saved. **The v2 prefix
has to earn that on every single turn of every single run.** On the live battery it did,
many times over, through lever 4 above. The scripted pass rate could never have shown
that, because the scripted backend does not read the prompt.

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
| Budget ceiling | **60,000 tokens/run** | Measured per-run cost. 0 of 60 scripted trials reach it, and the largest live run in the five batteries used 27,444 tokens (46%) |
| Monthly limit per user | **20 runs per member per month** | The busiest member in `data_A` has 8 of the 40 claims; 20 is 2.5× that. At the budget ceiling and Haiku's output price, one member's model spend is capped at US$6.00 a month, and a flood past it goes to a person |

**Make the stop loud.** A cap that silently returns an empty answer converts a visible
cost problem into an invisible correctness one — see [D7_failures.md](D7_failures.md),
where failure 2's whole point is that no cap could have detected it.
