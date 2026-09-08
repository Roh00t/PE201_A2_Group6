# D3(b) · Guardrail checklist

Owner: Huang Yu  
Backend: `scripted` only  
Cases: 15 total; 13 `must_fire`, 1 `must_not_fire`, 1 documented `known_limit`

## How to run

```bash
python3 evals/run_guardrails.py --twice
```

The runner creates a fresh temporary ledger for every case, restores its
temporary fixture/script changes after every case, and refuses to run on a live
backend. It exercises the shipped guardrail code, the real gated writer, and
the real narrative detector. It does not monkeypatch `Guardrails.*` or
`issue_decision_letter`.

## Coverage

The checklist covers:

- confirm and suggest autonomy holds, plus an act-mode control;
- step cap and measured token budget ceiling;
- identical action de-duplication;
- once-only decision writing even when the second call changes an argument;
- unknown claim, invalid decision, and fabricated/non-reconciling totals;
- three hostile narrative shapes: imperative instruction, tool imitation, and
  fabricated authority;
- a benign narrative control;
- one known paraphrase miss, recorded separately rather than hidden in the pass
  rate.

## Recorded result

The deterministic run produced:

| Counter | Result |
|---|---:|
| `must_fire` | 13/13 |
| `must_not_fire` | 1/1 |
| `known_limit` | 1 documented miss |
| `--twice` identical | `True` |

The machine-readable and rendered outputs are generated under
`results/scripted/guardrail_checklist__A__scripted__2026-09-08.*`.

The known limitation is deliberate: the current keyword-and-shape detector
does not catch every semantic paraphrase of a hostile request. It is documented
as a limitation and excluded from the pass denominator; it is not presented as
full prompt-injection resistance.

A scripted run proves that the guardrail fires when the agent attempts the bad action; whether a live model can be talked into attempting it is a D5(b) observation, not a guardrail result.

