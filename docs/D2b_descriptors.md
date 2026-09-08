# D2(b) · Problem A descriptors and the v1→v2 rewrite

Owner: Huang Yu  
Scope: the seven Problem A tools in `src/tools/tools.py`

## What is shipped

Every Problem A descriptor now exposes the six contract fields in the
model-facing prompt:

1. `NAME + SIGNATURE`
2. `WHAT`
3. `INPUT`
4. `RETURNS`, including a bounded shape where the tool returns a record
5. `FAILS WHEN`
6. `IRREVERSIBLE?`

`src/prompt.py` formats these fields explicitly. A missing descriptor is
therefore visible in `run_eval.py --prompt`, rather than silently leaving the
model to guess how a callable works.

The seven Problem A tools are all covered: `get_claim`, `lookup_policy`,
`lookup_hospital`, `check_coverage`, `get_preauthorisation`,
`check_duplicate_claim`, and `issue_decision_letter`.

## Poka-yoke decisions

| Boundary | What the v2 contract makes impossible or loud |
|---|---|
| `check_coverage(code, policy_id, documents_attached)` | Coverage cannot be checked without a non-empty policy id; unknown procedure codes and malformed document lists are rejected before lookup. |
| `get_preauthorisation(member_id, procedure_code, date_of_service)` | A pre-authorisation lookup cannot use an unknown procedure code or malformed date. The date is checked as an ISO date before the evidence lookup. |
| `issue_decision_letter(decision: Literal[...])` | The static contract names the three legal outcomes, and the runtime allow-list refuses any other string before a ledger write. |
| `issue_decision_letter(...)` totals and claim id | Unknown claims, negative/non-numeric totals, incomplete line counts, and non-reconciling approve totals are refused with `sent: false`; no ledger line is written. |

The type annotations are useful to readers and type checkers, but they are not
runtime validation in Python. The explicit checks at the tool boundary are the
runtime part of the poka-yoke.

## v1 and v2

v1 is a plausible first draft, not a sabotaged prompt. It has all seven tool
names and callable arguments, but uses weaker return descriptions, vague timing,
and generic failure text. It does not give the model the v2 size bounds,
near-miss warnings, required-document distinction, or the detailed totals and
duplicate constraints.

The v2 rewrite adds the information that changes decisions rather than merely
adding prose:

- `check_coverage` returns the required-document facts in the same call and
  distinguishes `document_attached: false` from `null`.
- `check_coverage` states that exclusion is line-level, not a claim-level
  escalation.
- `lookup_policy` highlights `remaining = annual_limit - used_to_date` and the
  three distinct policy escalation conditions.
- `get_preauthorisation` states that `None` means missing evidence, not
  uncovered care.
- `check_duplicate_claim` requires all four business facts and warns about
  one-fact near misses.
- `issue_decision_letter` states the one-write rule, the gate, the legal
  decision set, and the arithmetic it verifies.

## Prompt-size measurement

Measured locally with `prompt.build_system_prompt("A", version=...)` on the
same commit and same fixtures. The repository's `--prompt` audit reports the
rough size as `characters / 4`; the hashes below are over the prompt text only.

| Version | Characters | Rough tokens | SHA-256 |
|---|---:|---:|---|
| v1 | 4,963 | 1,240 | `36992f7881ece6174bf6be3990054a7d7a410f62e4a5ea64a367a436d180a0ad` |
| v2 | 8,601 | 2,150 | `4accfcfacda48e6b01d2dc492aae4351fc210610dc1f3fabb2f977124fabf705` |

The v2 prefix is longer, so it must earn its cost by preventing wrong calls or
turns. The measurement is intentionally a prompt comparison only; no live
model call was made for this change. The scripted backend does not read the
prompt, so its pass rate is not evidence that v2 is better than v1.

Reproduce the prompt audit with:

```bash
python3 run_eval.py --prompt
python3 evals/test_battery_fake.py
```


---

## Addendum · where the prefix cost actually sits

*Added 9 Sep by Rohit, from `prompt.format_descriptor` over the shipped set. The hashes
above were re-verified on the same commit and are unchanged.*

| Tool | v2 descriptor | share of prefix |
|---|---:|---:|
| `issue_decision_letter` | ~439 tok | 25% |
| `check_coverage` | ~376 tok | 21% |
| `check_duplicate_claim` | ~236 tok | 13% |
| `get_preauthorisation` | ~228 tok | 13% |
| `lookup_policy` | ~187 tok | 11% |
| `get_claim` | ~150 tok | 9% |
| `lookup_hospital` | ~140 tok | 8% |
| **total** | **~1,756 tok** | **82% of the 2,150-token v2 prompt** |

v1's seven descriptors total **~847 tok**. So the rewrite roughly **doubled** the block
that is re-billed on every turn: **+910 tokens per turn**, ~3,640 per run at our median
of 4 turns.

**That is a cost until the battery says otherwise.** It is lever 1 in
[D6_cost_model.md](D6_cost_model.md), and it is linear in `T` — for comparison, D2(c)'s
grouping change saved 20,520 input tokens per run, about six times what this spends. The
v2 prefix has to pay for itself in wrong calls prevented, and **only the live battery can
show that**, because the scripted backend never reads the prompt.

**What "did not help" would look like, so we cannot move the goalposts later:** v2 costs
more per run and does not raise the pass rate or the negative-case 3-of-3 rate on the
model held fixed. If that is what `evals/aggregate_battery.py` prints, that is what the
report says. `[brief D2(b)]`

### Two things D7 measured about these descriptors

- **The `check_coverage` widening carries a decision, not just prose.** Deleting the
  `required_document` / `document_attached` fields drops the set from 60/60 to 57/60 and
  flips `CLM-8901` to a silent wrong approval. See
  [D7_failures.md](D7_failures.md#failure-2--tool-interface--the-check_coverage-widening-deleted).
- **The required `policy_id` poka-yoke costs one turn per approval.** It makes "check
  coverage against no policy" impossible to express, and in exchange `check_coverage`
  cannot share a turn with the `lookup_policy` that feeds it. Measured and defended in
  [D2c_dependency_rule.md](D2c_dependency_rule.md).
