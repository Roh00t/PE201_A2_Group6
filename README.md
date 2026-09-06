# PE6201 A2 · Applied AI System — Group 6

**Problem A — health-insurance claim first response.** A single-agent ReAct loop that
reads a claim, checks the policy, works every line item, chases a pre-authorisation
where a procedure needs one, checks the hospital panel, and reaches exactly one of three
outcomes: **approve in principle · request a specific missing document · escalate to a
human assessor.**

The loop is hand-rolled. No framework owns it.

---

## Run it — clone to reproduced numbers in 4 commands, no API key

Python 3.9+. **Standard library only** — nothing to install.

```bash
git clone <this repo> && cd PE201_A2_Group6
python3 data/check_my_data.py                          # the fixtures hang together
python3 run_eval.py                                    # the whole evaluation set
python3 experiments/d2c_parallel_vs_sequential.py      # D2(c), both groupings
```

`BACKEND = "scripted"` is the committed default. Every command above is offline, free and
deterministic. Nothing here needs a key.

What the third command prints today:

```
Running all 40 labelled case(s) - 1 hand-scripted, 39 planned.
Grouping: parallel

  RESULTS   60 of 60 trials passed   (100%)
  trials              60
  median turns        4.0
  worst case turns    5
  hit the step cap    0
```

**Read that 100% correctly.** It is not a claim that our agent is good — see
[*What the scripted number does and does not mean*](#what-the-scripted-number-does-and-does-not-mean)
below. The honest pass rates come from the live battery (D5b).

Other entry points:

```bash
python3 run_eval.py CLM-8842        # one case, every turn, with the decision record
python3 run_eval.py --prompt        # exactly what a live model is sent, and its token cost
python3 experiments/demo_loop_failure.py   # D7 failure 1, before/after
```

---

## Where things are

```
run_eval.py                      the entry point a marker types
run_battery.py                   the entry point a member types on battery day
src/
  config.py                      BACKEND / MODEL / PROMPT_VERSION / caps — one block
  loop_agent.py                  the ReAct loop: multi-call turns, instrumentation
  prompt.py                      what the model is actually sent (D2b artefact)
  narrative_guard.py             hostile-text detection, in code (D3a)
  tools/tools.py                 7 tools + six-field descriptors
  backends/backends.py           scripted + live; ONE function knows a vendor exists
  backends/planner.py            derives the move sequence from the records (D5a)
  backends/guardrails.py         step cap · budget ceiling · de-duplication · gate
evals/
  harness.py                     code check + judgement queue
  run_eval.py                    argument handling and result-file naming
  run_battery.py                 D5(b) the live battery — the ONE script that spends
  battery_roster.json            one member, one model, one key — fill on the day
  battery_provenance.py          fingerprint, roster rules, derived trial count
  battery_checkpoint.py          fsync'd JSONL, resume, lock
  aggregate_battery.py           the report §3 table + the v1/v2 delta
  test_battery_fake.py           35 checks against a fake vendor, free
  guardrail_cases.json           D3(b) checklist            <- Huang Yu, in progress
data/
  make_fixtures_A.py             the generator — EXTRA_* block is where cases are added
  data_A/*.json                  generated; never hand-edited
  expected_outcomes_A.json       the answer key — 40 labels, written BY HAND
  check_my_data.py               ids resolve · shipped rows unchanged · every case labelled
  check_labels_A.py              our own: the arithmetic inside each label
experiments/
  d2c_parallel_vs_sequential.py  D2(c) measurement + the turn distribution
  demo_loop_failure.py           D7 failure 1, as a deletion from the working agent
results/scripted/                committed run output
logs/decisions.jsonl             the gated action's append-only record
docs/                            D0…D7 write-ups
```

---

## The evaluation set — 40 cases, 10 negative, 60 trials

| | |
|---|---|
| Cases | **40** — 15 shipped, 25 ours |
| Negative | **10** (7 escalate, 3 request_document) |
| Trials per model | **60** = 30 ordinary × 1 + 10 negative × 3 |
| Cost per member | ≈ **US$0.30** cheap tier · **US$2.94** mid tier |

**Declared: our set carries 10 negatives, not the 8 the brief expects, and that is
forced rather than chosen.** Nine of the fifteen shipped cases are already negative, and
the extension rule is *add rows with new ids, never edit or delete a shipped row*. So 9
is the floor for any set built on the shipped data, and 8 is unreachable without breaking
that rule. Ten sits inside the brief's stated 6–10 band, and at 60 trials the mid tier
comes in at US$2.94 — under the US$3-per-member warning line.

**Where our 25 cases concentrate, and why.** The shipped nine negatives already cover
every negative family in Appendix A — lapsed policy, outside dates, over the limit,
duplicate, missing pre-authorisation, missing document, and two hostile narratives. Adding
more negatives would have re-tested the same families at three times the trial cost. So our
extension goes mostly into **boundary and near-miss ordinary cases** — a claim exactly at
the remaining limit and one dollar under it, a pre-authorisation valid on its last legal
day, the first and last day of a policy window, and three duplicate near-misses that a
shortcut match wrongly escalates. Those near-misses are the most discriminating cases in the
set: an agent that matches duplicates on anything less than all four facts fails them.

We added one negative of our own, `CLM-9035`, because the extension guide requires at least
three negative cases to involve hostile free text and the shipped set supplies only two.

**The answer key is a submitted artefact.** `data/expected_outcomes_A.json` holds all 40
labels. Every one was written from Appendix A's routing table *before* the agent ran on it.

### Extending it

```bash
# 1 · edit the EXTRA_* lists near the bottom of data/make_fixtures_A.py
python3 data/make_fixtures_A.py     # 2 · regenerate data_A/
python3 data/check_my_data.py       # 3 · names anything broken or unlabelled
# 4 · add the label to data/expected_outcomes_A.json   <- BY HAND, from the routing table
python3 data/check_my_data.py       # 5 · "Your data hangs together."
python3 data/check_labels_A.py      # 6 · the arithmetic inside each label
```

Use ids that are obviously yours: claims from `CLM-9001`, members `M-7001`, policies
`POL-8001`. Never scroll up to edit a shipped row — `check_my_data.py` fingerprints every
one and will name the one that moved.

---

## What the scripted number does and does not mean

One case (`CLM-8842`) is hand-scripted move by move. The other 39 are produced by
`src/backends/planner.py`, which derives the move sequence from the claim record.

Everything else in the run is real: the loop, the tools, the guardrails, the gate, the
ledger, the instrumentation. Only the *model's choices* are simulated.

So the scripted pass rate is **close to 100% by construction** — the planner implements
the routing rule, and the key was written from the same routing rule. It is not evidence
that our agent is good. It is evidence that the **machinery reproduces**: that the loop
executes several tool calls in one turn, that the guardrails fire, that the gate holds,
that the ledger writes exactly once per approval, that turns and cost are counted.

The planner never reads `expected_outcomes_A.json` and contains no branch keyed to a claim
id. A planner that peeked would agree with the key by construction and measure nothing.

---

## The dependency rule (D2c)

```
Turn 1   get_claim                                              ALONE
Turn 2   lookup_policy || lookup_hospital || check_duplicate_claim
Turn 3   check_coverage × N        (one per line, independent of each other)
Turn 4   get_preauthorisation × M  (only the lines that need one)
Turn 5   issue_decision_letter                                  GATED
```

Measured both ways over the whole set, caps lifted so grouping is the only variable:

| grouping | turns | calls | input tokens | cost | pass rate |
|---|---|---|---|---|---|
| sequential | 356 | 360 | 2,314,800 | $0.2514 | 60/60 |
| parallel | 210 | 360 | 1,083,600 | $0.1213 | 60/60 |

**41% fewer turns, 53% fewer input tokens, correctness unchanged.** The call count is
identical — nothing was removed, the calls were regrouped, so the saving is the transcript
being re-sent fewer times.

Two things we will not claim. We do not quote the brief's 54%: that is CLM-8842's number
under the brief's grouping, not ours. And our `CLM-8842` takes **five** turns, not the
brief's four, because our `check_coverage` requires a `policy_id` — the D2(b) poka-yoke —
which turns a parallel pair into a chain. We pay one turn on every approval and get it back
on every escalation: a lapsed policy, a breached limit or a duplicate stops at **two turns**
without ever pricing a line.

---

## The caps, and where they came from

Measured, not chosen. Reproduce with `experiments/d2c_parallel_vs_sequential.py`.

```
turn distribution, 60 trials, parallel grouping
    2 turns  12 runs        median             4
    3 turns  12 runs        mean               3.50
    4 turns  30 runs        worst LEGITIMATE   5
    5 turns   6 runs        hit the cap        0

per-run tokens: median 21,600 · worst 29,520
```

`MAX_TURNS = 8` is the worst legitimate run (5) plus three. The margin is deliberate: the
planner never wanders, re-reads or mis-parses, so it is a **lower bound** on turns, and a cap
fitted tightly to scripted runs would truncate correct live ones. To be revisited after the
battery with real turn counts.

`MAX_TOKENS_PER_RUN = 60000` is the worst measured run doubled. **It is not slack** — run the
same work one call per turn and 11 of 60 trials breach it and halt. Our caps are calibrated
to the parallel grouping, and that dependency is stated rather than hidden.

Every stop is loud: the decision record carries `stopped_by` and the full `guardrails_fired`
list, so a cap never looks like a quiet wrong answer.

---

## The gated action

`issue_decision_letter` **does not write a letter.** It checks the gate, appends one
structured record to `logs/decisions.jsonl`, and returns a short confirmation. Three things
it enforces in code rather than asserting in a docstring:

1. **Once only per run** — a second decision on the same claim is blocked whatever its
   arguments.
2. **The claim exists** — a decision on an id that resolves to nothing is refused.
3. **The arithmetic is the record's, not the model's** — for an approve, `lines_resolved`
   and the two totals are re-derived from the claim and compared. A model that checked one
   line of four cannot write `lines_resolved: 4` and be believed.

Check 3 applies to approvals only: Appendix A's escalate example stops at two turns with the
lines deliberately never priced.

A cross-check that costs nothing: one clean run writes **30 ledger rows**, and the key holds
exactly **30 approve cases**. The gate fired once per approval and never on an escalate or a
request.

`AUTONOMY = "confirm"`, with the gate in front of the irreversible step rather than in front
of the agent.

---

## The live battery (D5b)

Six members, six keys, one evaluation set. The brief's warning is the design
constraint: *"with three runners drift is survivable; with six it silently voids the whole
battery."* **Silently** is the word — a drifted run produces a pass rate in the right format
at the right cost that is simply not comparable, and nobody gets an error.

```bash
python3 evals/test_battery_fake.py             # 35 checks, no key, no cost
python3 run_battery.py --member <name> --dry-run
python3 run_battery.py --member <name> --verify-drift   # paste this in the group chat
python3 run_battery.py --member <name>         # the live run. Spends YOUR key.
python3 evals/aggregate_battery.py             # the report §3 table
```

**Nobody edits `config.py`.** The runner mutates the module in memory from
`evals/battery_roster.json`. That is what makes the other controls possible: the worktree
stays genuinely clean so the dirty-refusal can fire, `config.py`'s hash can be pinned across
all six members, and six people are not editing the same three lines.

| Control | What it stops |
|---|---|
| Fingerprint over answer key, fixtures, plan, prompt text, pinned sources, invariants, commit | A run that is not comparable. Refuses and **names the component that moved** |
| Trial count **derived** from the fixtures | A roster that says 60 while the data says something else |
| `validate_roster()` | Two members on one family; a single price tier; a v1 pass on a model nobody ran |
| `getpass` → one local → `set_api_key()` | The key reaching `.env`, `os.environ`, a results file or a traceback |
| Canary on three case shapes | Committing to 60 runs on an estimate instead of a measurement |
| `--max-spend`, checked on **measured** cost after every trial | A battery quietly costing ten times its estimate |
| `max_tokens` on the request | A runaway completion. `MAX_TOKENS_PER_RUN` fires only *after* billing |
| `reasoning: {enabled: false}` | Hidden thinking billed as output at 4–5× |
| Retry at the **transport** layer | Re-spending turns 1–5 to retry a failure at turn 6 |
| 401/402/404 → immediate abort | Sixty exponential backoffs against a typo'd model id |
| fsync'd JSONL checkpoint + lock file | Losing 45 paid trials to a closed laptop; double-spending from a second terminal |

**Two negative numbers are reported, not one.** The negative *trial* rate and the negative
*3-of-3* rate are different findings, and the 3× policy exists to produce the second. A model
at 90% trial / 70% three-of-three is unreliable on refusals; one at 90%/90% is consistently
wrong about a single case.

**Before anyone spends:** the roster is filled on the day with prices verified that day, the
`v2-freeze` tag is cut, `--freeze` stamps the hashes, and all six paste identical
`--verify-drift` blocks. Member 1 then runs alone and everyone reads the file before the rest
follow.

---

## Contribution

| Strand | Feeds | Owner(s) |
|---|---|---|
| The loop and the tools | D1, D2(a), D2(c) | Rohit Panda, Xia Yanran |
| Descriptors, v1→v2 rewrite, guardrail layer | D2(b), D3 | Huang Yu, Rohit Panda |
| Evaluation harness and the scripted run | D4, D5(a) | Li Yunke, Huang Yu |
| Cost model, ledger, sensitivity | D6 | Shen Bowen, Zhao Yujia |
| Negative-case design, D7 failures | D3(b), D7 | Xia Yanran |
| Report and demo assembly | Report §§4–5 | Zhao Yujia, Shen Bowen |
| **Evaluation cases — 5–8 each** | D4 | **all six** |
| **Live model battery — one model each** | D5(b) | **all six** |

See `CONTRIBUTIONS.md`; the commit history corroborates it.

---

## Status

| | |
|---|---|
| D0 · Why an agent | `docs/D0c_what_good_looks_like.md` committed before any agent code |
| D1 · The agent | Done — multi-call turns, instrumented per run |
| D2(a) · Tool set | 7 tools, none added: `check_coverage` was widened instead |
| D2(b) · Descriptors | v2 shipped; the v1 *mechanism* is in (`tools.DESCRIPTORS_V1` + `prompt.descriptor_set`), the v1 *content* is Huang Yu's |
| D2(c) · Multi-tool turns | Measured both ways |
| D3(a) · Guardrail code | Step cap · budget ceiling · de-duplication · gate · narrative guard |
| D3(b) · Checklist | Outstanding |
| D4 · Evaluation set | 40 cases, 10 negative, code + judgement checks |
| D5(a) · Scripted run | Reproduces from a clean clone, no key |
| D5(b) · Live battery | Runner, provenance, checkpoint, aggregator and 35-check rehearsal all in. Roster unfilled; no live run yet |
| D6 · Cost model | Outstanding |
| D7 · Two failures | Failure 1 done; failure 2 outstanding |

## Known limits

- The scripted pass rate is 100% by construction and is not a claim about agent quality.
- `narrative_guard.py` is a keyword-and-shape tripwire over three rules. It catches all
  three injection cases with no false positives across 40 narratives, but it will not catch
  a paraphrase it has never seen. The real boundary is that the narrative never reaches a
  tool argument and cannot change what `policies.json` says.
- Scripted guardrail runs prove a guardrail fires when the agent *attempts* a bad action.
  Whether a live model can be talked into attempting it is a D5 observation, not a
  guardrail case.
- `docs/lecturer_clarifications.md` records where two course documents disagree and what we
  assumed instead.
