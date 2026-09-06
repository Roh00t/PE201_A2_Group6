# PE201 A2 · Group 6

Health-insurance claim first-response agent for PE6201 Assignment 2, Problem A.

## Current Status

This repository is at the scaffold and partial implementation stage as of 6 September 2026. The status below is based on files currently checked in or present in the workspace; planned work is not counted as complete.

### Completed or substantially present

- D0(c): five testable statements describing what a good run must do in [docs/D0c_what_good_looks_like.md](docs/D0c_what_good_looks_like.md).
- Local Problem A reference data and answer labels: 50 claims plus policy, member, hospital, procedure, pre-authorisation, required-document, and decided-claim tables under [data/data_A](data/data_A).
- Data validation utilities: [data/check_my_data.py](data/check_my_data.py) and [data/check_labels_A.py](data/check_labels_A.py).
- A hand-written ReAct-style loop in [src/loop_agent.py](src/loop_agent.py), including multi-call turns, observation accumulation, per-run turn/token/cost instrumentation, and loud guardrail stops.
- Scripted and live backend concepts in [src/backends/backends.py](src/backends/backends.py), with one vendor-specific OpenRouter call site and a scripted backend design.
- A shared configuration module in [src/config.py](src/config.py), including a scripted backend default, model settings, autonomy mode, turn cap, and token ceiling.
- Problem A tool implementations and descriptors in [src/tools/tools.py](src/tools/tools.py), including the claim lookup, policy/coverage checks, pre-authorisation lookup, hospital lookup, and gated decision action.
- Prompt construction and six-field descriptor formatting in [src/prompt.py](src/prompt.py).
- Evaluation harness structure and deterministic code-check/judgement-check split in [evals/harness.py](evals/harness.py), plus grader scaffolding under [evals/graders](evals/graders).
- A D7 loop-failure demonstration scaffold in [experiments/demo_loop_failure.py](experiments/demo_loop_failure.py).
- The implementation plan and course reference material under [docs/plan](docs/plan) and [docs/course](docs/course).

### Partially complete or not yet complete

- The repository default is still `PROBLEM = "B"` in `src/config.py`, although the assignment target is Problem A. Problem B fixture data is not present in this checkout.
- The offline entry point is not integrated from the repository root. `evals/run_eval.py` imports modules that are not currently available under those names (`agent`, `backends`, and related package imports), and Python package marker files are absent.
- Problem A has a scripted example for `CLM-8842`, but the scripted backend does not yet cover the full 40-case evaluation run.
- D3(b) is not complete: [evals/guardrail_cases.json](evals/guardrail_cases.json) is empty.
- D2(c) is not complete: [experiments/d2c_parallel_vs_sequential.py](experiments/d2c_parallel_vs_sequential.py) is empty.
- D4 is not complete: there is no repository-owned 40-case evaluation file with 32 ordinary and 8 negative cases, and no recorded 56-trial scripted result.
- D5(b) live model results are not present. No live battery should be treated as completed from the current files.
- D6 cost analysis is not present as an executable model or results table.
- D7 has only the loop-failure demonstration scaffold; the required full-evaluation before/after evidence and a second non-loop failure are still outstanding.
- The final team declaration, contribution record, report, and demo artefacts are not yet represented as completed deliverables in this README.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `src/` | Configuration, ReAct loop, prompt, backends, guardrails, and tools |
| `data/data_A/` | Problem A local fixture tables |
| `evals/` | Evaluation harness, graders, and guardrail-case placeholder |
| `experiments/` | D2(c) and D7 experiment entry points |
| `results/` | Reserved for scripted, live, and v1/v2 evidence |
| `logs/` | Decision ledger location |
| `docs/` | D0(c), implementation plan, course material, and notes |

## Running the Current Code

The intended marker command is:

```bash
python3 evals/run_eval.py
```

At present this command is a target integration check, not a passing clean-clone command. The current configuration and import/package issues described above must be resolved before claiming D5(a) reproducibility.

The intended live backend requires an environment variable and incurs API cost:

```bash
export OPENROUTER_API_KEY="..."
```

Do not commit the key. Development and guardrail work should remain on the scripted backend.

## Next Blocking Work

1. Make the Problem A path the default and repair the package/module entry points.
2. Add the repository-owned scripted cases and run the data/label checks.
3. Populate the guardrail checklist and D2(c) experiment, then record their outputs.
4. Build the 40-case D4 harness run before spending tokens on live models.
5. Add D6 results and complete both D7 failure reproductions from the working implementation.

The full requirements and submission gates are tracked in [docs/plan/Project_Implementation_Plan.md](docs/plan/Project_Implementation_Plan.md). The current implementation should be judged against that plan, not against the scaffold comments that describe future work.

