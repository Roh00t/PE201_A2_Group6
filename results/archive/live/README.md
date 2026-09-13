# Superseded battery runs — kept as evidence, excluded from the table

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
