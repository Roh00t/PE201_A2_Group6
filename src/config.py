"""
PE6201 · A2 scaffold — CONFIGURATION
====================================================================
THIS IS THE VENDOR-NEUTRAL BLOCK THE BRIEF ASKS FOR (D5).

Everything that knows which model you are using lives here and in
backend_live.py, and nowhere else. Switching model is changing a string.

    BACKEND = "scripted"   free, deterministic, no key, no network.
                           THIS MUST BE THE DEFAULT IN WHAT YOU SUBMIT.
                           A marker clones your repository and runs it
                           this way. If it does not run, D5(a) fails and
                           Technical Execution is capped.

    BACKEND = "live"       real model through OpenRouter. Costs money.
                           Only D5(b) - your model battery - needs this.

The guardrail checklist (D3b), the reproducible run (D5a) and the two
failure reproductions (D7) ALL run scripted. Only the battery is live.
====================================================================
"""
import os

# ─────────────────────────────────────────────────────────────────────
# THE THREE STRINGS. Change these, change nothing else.
# ─────────────────────────────────────────────────────────────────────
BACKEND = "scripted"          # "scripted" | "live"

MODEL = "openai/gpt-4o-mini"  # only used when BACKEND == "live"
BASE_URL = "https://openrouter.ai/api/v1"

# WHICH DESCRIPTOR SET THE PROMPT IS BUILT FROM (D2b).
#   "v2"  the descriptors we ship  - the battery runs this, on every model
#   "v1"  the deliberately worse ones - ONE model only, for the comparison
# Stamped into every result file, because a pass rate that cannot be
# traced to a prompt version is not a measurement. Change one thing at a
# time: to compare prompt versions hold MODEL fixed; to compare models
# hold PROMPT_VERSION fixed.
PROMPT_VERSION = "v2"

# Your key never goes in this file. Two ways in, and BOTH work:
#     export OPENROUTER_API_KEY="sk-or-..."      (shell, or Colab os.environ)
#     config.set_api_key("sk-or-...")            (runtime, what run_battery uses)
#
# WHY api_key() IS A FUNCTION. The module-level read below happens exactly
# ONCE, at import. So the intuitive move -
#     import config
#     os.environ["OPENROUTER_API_KEY"] = key     # too late!
# - leaves API_KEY empty and produces a confusing "key is not set" exit
# from a key you just supplied. Reading the environment at CALL time makes
# the intuitive move work too. The wrong thing looking right is exactly
# the class of bug this file's stale-bytecode warning already exists for.
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")   # legacy shim; prefer api_key()

_API_KEY_RUNTIME = None


def set_api_key(value):
    """Supply the key AFTER import, without touching os.environ.

    run_battery.py uses this deliberately: a key placed in the process
    environment leaks into every subprocess and into crash dumps, and
    students paste tracebacks into group chats.
    """
    global _API_KEY_RUNTIME
    _API_KEY_RUNTIME = value or None


def api_key():
    """The key, read at CALL time. Runtime override first, env second."""
    return _API_KEY_RUNTIME or os.environ.get("OPENROUTER_API_KEY", "") or API_KEY

# ─────────────────────────────────────────────────────────────────────
# WHICH PROBLEM. "A" = claims first response, "B" = referral coordination.
# ─────────────────────────────────────────────────────────────────────
PROBLEM = "A"

# ─────────────────────────────────────────────────────────────────────
# GUARDRAIL LIMITS (D3a). These are the code layer. Set them from
# EVIDENCE, not from a round number - see D7. If your median run is 4
# turns and your worst legitimate run is 7, a cap of 8 is defensible
# and a cap of 30 is decoration.
# ─────────────────────────────────────────────────────────────────────
# WHERE THESE TWO NUMBERS CAME FROM. Measured, not chosen. Run
# `python3 experiments/d2c_parallel_vs_sequential.py` to reproduce the
# distribution below on the scripted backend, free, in seconds.
#
#   turn distribution, 60 trials over 40 cases, parallel grouping:
#       2 turns  12 runs      median            4
#       3 turns  12 runs      mean              3.50
#       4 turns  30 runs      worst LEGITIMATE  5
#       5 turns   6 runs      hit the cap       0
#
#   per-run tokens: median 21,600 · worst 29,520 · worst cost US$0.00317
#
# STEP CAP 8 = worst legitimate (5) + 3. The margin is deliberate and it
# is not padding: the planner is a LOWER BOUND on turns, because it never
# wanders, never re-reads and never mis-parses. A live model does all
# three, so a cap fitted tightly to scripted runs would truncate correct
# live ones. Revisit this after the D5(b) battery with real turn counts.
# A cap of 5 would cut the longest correct run in the set; a cap of 30
# would be decoration.
#
# BUDGET CEILING 60,000 = worst measured run (29,520) x ~2, same logic.
# Note it is NOT slack: at one call per turn, 11 of 60 trials breach this
# ceiling and halt. Our caps are calibrated to the grouping in GROUPING
# below, and that dependency is stated in the report rather than hidden.
MAX_TURNS = 8                 # step cap
MAX_TOKENS_PER_RUN = 60000    # budget ceiling
AUTONOMY = "confirm"          # "suggest" | "confirm" | "act"

# ---------------------------------------------------------------------
# DUPLICATE-ACTION RECOVERY. How many times a repeated call is answered
# with a correction instead of halting the run.
#
# ZERO IS THE SHIPPED DEFAULT AND IT MUST STAY ZERO. At 0 the guard
# behaves exactly as D3(a) describes and as D3(b)'s GR-06 asserts: an
# identical repeat halts the run with stopped_by="duplicate_action".
# Raising it globally would quietly weaken a guardrail we claim to have.
#
# Above 0, the repeat is fed back to the model as an observation and the
# run continues, up to N times, before the hard stop. The guard still
# FIRES and is still recorded every time - it stops being a kill-switch
# and becomes a correction, which is a different claim and has to be
# reported as one.
#
# Set per-run from the roster (`duplicate_recovery_retries`), never here.
DUPLICATE_RECOVERY_RETRIES = 0
#   suggest  - the agent proposes; a human does everything
#   confirm  - the agent does everything EXCEPT the irreversible step,
#              which waits for a yes. THE GATE GOES IN FRONT OF THE
#              IRREVERSIBLE STEP, not in front of the agent.
#   act      - the agent completes the irreversible step itself

# HOW CALLS ARE GROUPED INTO TURNS (D2c). "parallel" applies our
# dependency rule; "sequential" runs one call per turn. The same work,
# grouped two ways - which is the measurement D2(c) asks for. See the
# rule itself, written out, at the top of src/backends/planner.py.
GROUPING = "parallel"         # "parallel" | "sequential"

# ─────────────────────────────────────────────────────────────────────
# LIVE TRANSPORT (D5b). Only used when BACKEND == "live".
# ─────────────────────────────────────────────────────────────────────
# MAX_TOKENS_PER_CALL is a SPEND control and MAX_TOKENS_PER_RUN is not:
# the run guardrail fires AFTER the tokens are billed, so it bounds the
# damage of a runaway completion but cannot prevent it. This caps the
# request itself. Output bills at 4-5x input, so this is the cheapest
# guardrail in the file.
MAX_TOKENS_PER_CALL = 1024
TEMPERATURE = 0
HTTP_TIMEOUT = 60
RETRY_MAX = 5
RETRY_BASE_SECONDS = 2.0

# Reasoning models bill hidden thinking as OUTPUT. The brief recommends
# against one for A2 and `reasoning: exclude` hides the tokens while
# still charging for them. Off by default; run_battery --allow-reasoning
# turns it on, caps it, and says so loudly at pre-flight.
ALLOW_REASONING = False

# Set True by run_battery when it mutates this module in memory, so the
# stale-bytecode detector does not cry wolf on every live run.
RUNTIME_OVERRIDE = False

# ─────────────────────────────────────────────────────────────────────
# WHERE THE DATA IS. The scaffold ships in its own folder, so it looks
# for the reference data next door. If you moved things, set the
# environment variable A2_DATA instead of editing this.
# ─────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))

_CANDIDATES = [
    os.environ.get("A2_DATA", ""),
    os.path.join(HERE, "..", "A2_reference_data"),
    os.path.join(HERE, "A2_reference_data"),
    os.path.join(HERE, "..", "fixtures"),
    os.path.join(HERE, "..", "data"),
    os.path.join(HERE, ".."),
]


def data_root():
    """Find the folder that holds the selected problem's fixture data.

    Fails LOUDLY with instructions rather than returning something wrong.
    A silent wrong path here is exactly the failure the data guide warns
    about: your tools return nothing and the run still looks fine.
    """
    data_dir = "data_%s" % PROBLEM
    for c in _CANDIDATES:
        if c and os.path.isdir(os.path.join(c, data_dir)):
            return os.path.abspath(c)
    raise SystemExit(
        "\n  Could not find the reference data.\n"
        "  I looked for a folder containing %s/ in:\n" % data_dir
        + "".join("    %s\n" % os.path.abspath(c) for c in _CANDIDATES if c)
        + "\n  Fix it either way:\n"
        + "    1. keep the data_%s/ folder in the repository data root, or\n" % PROBLEM
        + "    2. export A2_DATA=/path/to/A2_reference_data\n")


# ─────────────────────────────────────────────────────────────────────
# PRICES, US dollars per MILLION tokens. Section 7 of the brief.
# Checked against vendor pages 28 August 2026. RE-CHECK THEM: quoting a
# price you did not verify is the kind of thing D6 is marked on.
# ─────────────────────────────────────────────────────────────────────
PRICE_IN = 0.10
PRICE_OUT = 0.40


def _stale_bytecode_warning():
    """Detect Python reusing an out-of-date __pycache__ copy of THIS file.

    WHY THIS EXISTS. Changing PROBLEM = "B" to "A" edits one character and
    leaves the file the SAME SIZE. If the edit lands in the same second as
    the last run, Python's staleness check - (source mtime, source size) -
    sees no change and silently reuses the compiled copy. You edit the
    file, run it, and get the OLD value with no error at all.

    That happened during development of this scaffold, so it will happen
    to you. It is also a small lesson in its own right: the most expensive
    bugs are the ones that produce a confident, wrong, unremarkable answer.

    The fix is `rm -rf __pycache__`, or in a notebook, restart the kernel.
    """
    import re
    if RUNTIME_OVERRIDE:
        # run_battery sets BACKEND/MODEL in memory ON PURPOSE, so the file
        # and memory SHOULD disagree. Warning here would put a false
        # "STALE BYTECODE" banner into every live results file.
        return ""
    try:
        src = open(os.path.join(HERE, "config.py"), encoding="utf-8").read()
    except OSError:
        return ""
    out = []
    for name, live in (("PROBLEM", PROBLEM), ("BACKEND", BACKEND)):
        m = re.search(r'^%s\s*=\s*"([^"]*)"' % name, src, re.M)
        if m and m.group(1) != live:
            out.append("%s is %r in config.py but %r in memory"
                       % (name, m.group(1), live))
    if not out:
        return ""
    return ("\n  !! STALE BYTECODE - PYTHON IS IGNORING YOUR EDIT !!\n"
            + "".join("     %s\n" % o for o in out)
            + "     fix:  rm -rf __pycache__      (in a notebook: restart the kernel)\n")


def summary():
    """One line, printed at the top of every run, so you always know
    which backend produced the numbers you are looking at.

    It also carries the stale-bytecode check, because this line is the
    one place every entry point already prints."""
    where = "FREE, deterministic" if BACKEND == "scripted" else "LIVE - this costs money"
    model = "(no model)" if BACKEND == "scripted" else MODEL
    line = ("BACKEND=%s  %s  |  PROBLEM=%s  |  model=%s  |  "
            "cap=%d turns  |  autonomy=%s"
            % (BACKEND, where, PROBLEM, model, MAX_TURNS, AUTONOMY))
    return line + _stale_bytecode_warning()
