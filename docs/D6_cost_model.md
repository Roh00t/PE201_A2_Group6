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
