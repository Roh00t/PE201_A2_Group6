# D2(a) · The tool set, scored

Owner: Rohit Panda · Xia Yanran
Set: **7 tools**, Problem A, `src/tools/tools.py` → `REGISTRY["A"]`

> The brief credits four justified tools over eleven, and gives explicit credit
> for a tool **removed** with the observation that removed it. `[brief D2(a)]`

Reproduce every number below with:

```bash
python3 run_eval.py --prompt
```

---

## 1 · Before adding a tool, we tried not adding one

Four moves, in the brief's order of preference. What we actually tried:

| Move | Where we used it | Result |
|---|---|---|
| **Widen an existing tool's parameters** | `check_coverage(code, policy_id)` → `check_coverage(code, policy_id, documents_attached)` | A `get_required_documents` tool was **not added**. Its job became a third argument. |
| **Return more from one call** | `check_coverage` now also returns `required_document` and `document_attached` | The required-document question is answered in the same call that answers coverage. One turn, not two. |
| **Move the step into ordinary code** | Hostile-narrative detection → `src/narrative_guard.py` | **No tool at all.** Deterministic, free, runs outside the loop, and cannot be talked out of firing because the model never calls it. |
| **Only then add a tool** | `check_duplicate_claim` | Added, because nothing else in the set can see decided-claim history. |

**D7 failure 2 is the receipt for row 1.** Deleting the widening drops the set
from 60/60 to 57/60 and flips `CLM-8901` from `request_document` to
`approve_in_principle` — a silent wrong answer in the expensive direction. The
widening is not tidiness; it carries a decision. See [D7_failures.md](D7_failures.md).

---

## 2 · The three questions, scored

**Q1 — does a task fail without it?**
**Q2 — could the model confuse it with a neighbour?**
**Q3 — what does it cost when it is never called?** Its descriptor sits in the
prefix and is **re-billed on every turn** whether or not it is called. That is
lever 1 in D6, and it is linear in `T`.

Descriptor sizes are measured, not estimated — `prompt.format_descriptor` over
the shipped v2 set:

| Tool | Q1 · fails without it | Q2 · confusable with | Q3 · prefix cost/turn | Verdict |
|---|---|---|---:|---|
| `get_claim` | **Yes.** Nothing downstream has a member, hospital, date or lines without it. | Nothing. It is the only entry point. | ~150 tok | **Keep** |
| `lookup_policy` | **Yes.** Live-dates, annual limit and remaining balance exist nowhere else; two of the three escalation triggers read them. | Weakly with `check_coverage` — both say "policy". Split by object: this one answers *about the member's policy*, that one *about one procedure line*. | ~187 tok | **Keep** |
| `check_coverage` | **Yes.** Per-line exclusion, pre-auth requirement and required-document facts. | With `lookup_policy` (see above) and `get_preauthorisation` — it says a pre-auth is *required*, it does not say one *exists*. | ~376 tok | **Keep** |
| `get_preauthorisation` | **Yes.** Whether an approval exists and is valid on the date of service. | With `check_coverage`. The descriptor states the split explicitly, and `None` means *missing evidence*, never *uncovered care*. | ~228 tok | **Keep** |
| `lookup_hospital` | **Marginal — kept deliberately.** No case in our 40 turns on panel status alone. It changes what the record must **say**, not what the decision **is**. | Nothing. | ~140 tok | **Keep, with the weakness stated** |
| `check_duplicate_claim` | **Yes.** Decided-claim history is a separate system of record; a resubmission arrives with a new claim id, so no other tool can see it. | Nothing. | ~236 tok | **Keep** |
| `issue_decision_letter` | **Yes.** The only write, and the only irreversible step. | Nothing — and the autonomy gate sits in front of exactly this one. | ~439 tok | **Keep, gated** |

**Total: ~1,756 tokens of descriptors, 82% of a 2,150-token v2 prefix.**

### `lookup_hospital` is our `search_notes`

The brief asks us to find the tool that fails questions 1 and 2. *"If we cannot
name one, we have not scored honestly."*

`lookup_hospital` is it. **No case in the evaluation set fails without it.** Panel
status never changes the outcome — it changes what the decision record must state.
It is 140 tokens on every turn of every run for a fact that decides nothing.

**We kept it, and the reason is a limit rather than a defence.** Appendix A names
panel status as something the record must carry, and our own D0(c) statement 1
requires a decision to name a cause traceable to a record. Dropping the tool would
save ~140 tokens/turn (~8% of the prefix, ~2.6% of a 4-turn run's input) and make
our own record incomplete against the brief's own routing table.

**What would settle it:** an evaluation case where an off-panel hospital changes
the outcome. We do not have one, so we cannot claim the tool earns its place on
evidence — only that removing it breaks a stated record requirement. That is the
honest version and it is stated as a limit in report §6.

---

## 3 · What we cut

| Candidate tool | Why it does not exist |
|---|---|
| `get_required_documents` | **Folded into `check_coverage`.** Same call, three extra fields, one fewer turn. D7 failure 2 measures what the folding is worth: 3 trials. |
| `check_narrative` / `detect_injection` | **Not a tool.** Moved to `src/narrative_guard.py`, ordinary code outside the loop. A tool the model chooses to call is a tool the model can choose not to call — and hostile text is exactly the input that would argue for skipping it. Three of our four hostile guardrail cases turn on this. |
| `get_hospital_status` (Appendix A's name) | **Renamed** `lookup_hospital`, to sit in the same `lookup_*` family as `lookup_policy`. Appendix A's names are suggestions. `[upd]` |
| `calculate_total` / `sum_lines` | **Not a tool.** Arithmetic the code does at the boundary. `issue_decision_letter` re-derives the totals from the claim record and refuses to write a ledger line if they do not reconcile — a poka-yoke, not a callable. |
| `get_member` | **Not needed.** `get_claim` returns `member_id`, and `lookup_policy` takes it. A tool whose entire output is one field of another tool's output is a turn we would be paying for twice. |

---

## 4 · What the scoring changed

Two things, both measurable:

1. **`check_coverage` got wider instead of the set getting longer.** A
   `get_required_documents` tool would have added ~150 tokens to every turn's
   prefix *and* a turn to every claim carrying a documented procedure.
2. **The set is 7, not 9.** The two we did not build (`get_required_documents`,
   `detect_injection`) would have cost roughly 300 tokens per turn between them.
   On a 4-turn median run that is ~1,200 input tokens per run — about 6.6% of the
   measured 18,060.

Levers 1 and 3 look similar and are not: a fat tool block is **linear** in `T`, a
fat observation **compounds**. Both are priced in [D6_cost_model.md](D6_cost_model.md).
