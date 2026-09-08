# D2(c) · The dependency rule, and what parallel calling saved

Owner: Rohit Panda
Rule in code: `src/backends/planner.py` · Measurement: `experiments/d2c_parallel_vs_sequential.py`

```bash
python3 experiments/d2c_parallel_vs_sequential.py     # free, deterministic
```

> We must state our rule, measure both ways, and show correctness did not move.
> `[upd]` Report **our** measured saving. The brief's 54% belongs to CLM-8842's
> example, not to us.

---

## 1 · The rule, written down before it was coded

**A pair of calls may share a turn only when neither needs the other's output.**
Everything else is a chain, and a chain cannot be shortened by firing it at once.

| Turn | Calls | Why they group — or why they cannot |
|---|---|---|
| 1 | `get_claim` **alone** | Everything downstream needs the member, the hospital and the line items it returns. |
| 2 | `lookup_policy` ‖ `lookup_hospital` ‖ `check_duplicate_claim` | Three calls that need only the claim record, and none of which needs another's output. |
| 3 | `check_coverage` × N (one per line) | Independent **of each other**, so one turn — but **not** independent of turn 2, because our `check_coverage` requires a `policy_id` and only `lookup_policy` can supply one. |
| 4 | `get_preauthorisation` × M | Cannot join turn 3: we do not know **which** line requires an approval until coverage has answered. |
| 5 | `issue_decision_letter` | **A turn like any other.** Gated, not free, and counted. |

---

## 2 · Where we diverge from Appendix A, and why

Appendix A folds `lookup_policy` and `check_coverage` into one turn and reaches
`CLM-8842` in **four** turns. We reach it in **five**.

The reason is our own poka-yoke: `check_coverage(code, policy_id, ...)` takes a
**required** `policy_id`. That makes "check coverage against no policy" impossible
to express — and it also turns a parallel pair into a chain. **The poka-yoke costs
us one turn on every approval.** That is a real, measured trade between D6's lever
2 (turn count) and an interface constraint, and we accept it.

The brief anticipates exactly this: *"a team that parallelises less than we did and
explained why is on stronger ground than one that copied this page"*, and *"D2(c)
marks your reasoning, not your number."*

### A defect this rule caught in our own code

Until 9 September the hand-written script for `CLM-8842` in
`src/backends/backends.py` fired `lookup_policy` and all three `check_coverage`
calls **in the same turn**, passing `policy_id: "POL-3310"` alongside the
`lookup_policy` call that produces it. It matched Appendix A's four-turn shape.

It only worked because a hand-written script already knows the answer. **No live
model could reproduce that turn**, so the scripted baseline was measuring a shape
the D5(b) battery could never match — a scripted run and a live run that are not
comparable is precisely the failure the battery's provenance layer exists to
prevent, arriving from the other direction.

The turn is now split. `CLM-8842` costs 5 turns, the headline saving is unchanged,
and the number is one a live model can actually hit.

### What the rule buys back

Because turn 2 is **claim-level only**, a lapsed policy, a breached annual limit
or a duplicate escalates at **two turns** without ever pricing a line. That is
Appendix A's `CLM-8925` record, and it is the early-exit case D4 asks for: pricing
lines the claim will never pay is burned turns.

**12 of 60 trials finish in 2 turns.** A rule that parallelises less at the top
finishes sooner at the bottom.

---

## 3 · Measured both ways · 60 trials, same set, same commit

| grouping | turns | tool calls | input tokens | cost | pass rate |
|---|---:|---:|---:|---:|---|
| sequential (one call per turn) | 357 | 360 | 2,322,600 | US$0.2523 | **60/60** |
| parallel (our rule) | 211 | 360 | 1,091,400 | US$0.1221 | **60/60** |

### **41% fewer turns · 53% fewer input tokens · correctness did not move**

**The call count is identical — 360 both ways.** Nothing was removed; the calls
were only regrouped. So the entire saving is the transcript being re-sent fewer
times, which is `input ≈ B·T + D·T(T−1)/2` behaving as advertised: turns fell 41%,
and because the second term is quadratic in `T`, input tokens fell by more.

We use the **Class 5 exact form** `B·T + D·T(T−1)/2`, matching the brief's worked
examples, not Class 4's `D·T²/2` approximation.

---

## 4 · The honest limits on that number

Two, both stated rather than buried.

**(a) The saving is measured with the caps lifted.** With the shipped caps in
place:

| grouping | passed | halted by a guardrail | hit the step cap |
|---|---:|---:|---:|
| sequential | 49/60 | 11 | 0 |
| parallel | **60/60** | 0 | 0 |

Our caps are calibrated to the **parallel** grouping. Run the same work one call
per turn and 11 trials breach the budget ceiling and halt — not because the answer
was wrong, but because the run got long. **A cap is only defensible alongside the
grouping it was derived under.** That is D7's lesson arriving early, and it is why
the 41%/53% figures are quoted from the caps-lifted arm and labelled as such.

**(b) This is the scripted backend.** It proves the *grouping* is correct and
prices it exactly. It does not prove a live model will group the same way — that
is a D5(b) observation. The scripted arm is the control, not the claim.

---

## 5 · Where the cap numbers come from

| turns | runs |
|---:|---|
| 2 | 12 |
| 3 | 12 |
| 4 | 29 |
| 5 | 7 |

median **4** · mean **3.52** · worst legitimate **5** · hit the cap **0**

`MAX_TURNS = 8` is the worst legitimate run **plus three**, for a model that
wanders once and recovers. A cap of 30 would be decoration; a cap of 5 would
truncate the longest correct run in the set. `MAX_TOKENS_PER_RUN = 60,000` is
derived the same way from measured per-run cost — see `src/config.py`, where the
comment carries the evidence rather than the round number.
