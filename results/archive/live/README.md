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

The second is the one worth citing in D7: it is a clean demonstration that a
pass rate can be dominated by a defect in the harness rather than by the model
under test, and that a 100% scripted run cannot detect it — `ScriptedBackend`
ignores the transcript by design.

Inspect either with:

```bash
python3 evals/metrics.py results/archive/live/<file>.json
```
