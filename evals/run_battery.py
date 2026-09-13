#!/usr/bin/env python3
"""
PE6201 · A2 — THE LIVE MODEL BATTERY  (D5b)
====================================================================
    python3 run_battery.py --member rohit

THIS SPENDS REAL MONEY ON YOUR OWN KEY. Everything else in this
repository is free; this is the one script that is not.

WHAT IT IS FOR. Six members run the same 40-case evaluation set on
different models and the numbers land in one table. For that table to
mean anything, exactly one thing may differ between the six runs: the
model. The brief is blunt about what happens otherwise - "with six it
silently voids the whole battery" - and SILENTLY is the word. A drifted
run produces a pass rate in the right format at the right cost that is
simply not comparable with anyone else's, and nobody gets an error.

So this script's real job is not running trials. harness.run_set already
does that, and this file deliberately does not fork it. Its job is to
make every way the battery could be quietly invalidated LOUD:

    nobody edits config.py       - it is mutated in memory, so the
                                   worktree stays clean and its hash can
                                   be pinned across all six members
    the fingerprint refuses      - and names the component that moved
    the trial count is derived   - never typed, so it cannot disagree
                                   with the fixtures
    the key is never written     - getpass, one local, never os.environ,
                                   never the results file
    the spend is capped          - measured after every trial, not
                                   estimated once at the start
    the run resumes              - 60 live calls will not all survive

    python3 run_battery.py --member rohit --dry-run   proves all of the
    above against the scripted backend, for free, before a dollar moves.
====================================================================
"""
import argparse
import datetime
import getpass
import json
import os
import statistics
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import config                                              # noqa: E402
from backends import backends                              # noqa: E402
from tools import tools                                    # noqa: E402
from evals import battery_checkpoint as ckpt               # noqa: E402
from evals import battery_provenance as prov               # noqa: E402
from evals import harness                                  # noqa: E402

LIVE_DIR = os.path.join(ROOT, "results", "live")


# =====================================================================
# THE KEY
# =====================================================================
def obtain_key(dry_run=False):
    """getpass, held in one local, never persisted anywhere.

    NOT os.environ, deliberately. A key in the process environment is
    inherited by every subprocess and appears in crash dumps, and
    students paste tracebacks into group chats. `config.set_api_key`
    keeps it in one module-level variable that nothing serialises.
    """
    if dry_run:
        return "sk-or-DRYRUN-no-network-will-be-touched"
    env = os.environ.get("OPENROUTER_API_KEY", "")
    if env:
        print("\n  WARNING: OPENROUTER_API_KEY is set in your environment.")
        print("  That key is inherited by every subprocess you launch and")
        print("  can surface in a traceback. Prefer `unset OPENROUTER_API_KEY`")
        print("  and let this prompt take it instead.\n")
    key = getpass.getpass("  OpenRouter API key (input hidden, never stored): ")
    key = key.strip()
    if not key:
        raise SystemExit("  No key given. Nothing was run and nothing was spent.")
    if not key.startswith("sk-or-"):
        raise SystemExit("  That does not look like an OpenRouter key "
                         "(expected it to start 'sk-or-'). Nothing was run.")
    print("  key accepted · ...%s   (last 4 shown; never written to disk)"
          % key[-4:])
    return key


def install_scrubbing_excepthook(key):
    """Never let the key reach a terminal via a traceback."""
    original = sys.excepthook

    def scrub(exc_type, exc, tb):
        import traceback
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        sys.stderr.write(text.replace(key, "sk-or-***REDACTED***"))

    sys.excepthook = scrub
    return original


def assert_no_secret(text, key):
    """Last line of defence before anything is written to disk."""
    if key and key in text:
        raise SystemExit(
            "  REFUSING TO WRITE: the API key appears in the output. "
            "This is a bug - report it rather than working around it.")
    if "sk-or-" in text:
        raise SystemExit(
            "  REFUSING TO WRITE: something shaped like an OpenRouter key "
            "appears in the output.")


# =====================================================================
# PRICES — verified on the day, per the brief
# =====================================================================
def fetch_price(model, timeout=20):
    """Live per-token price from OpenRouter's public /models endpoint.

    The brief requires prices verified on the day with the date recorded;
    a price read off a slide from August is not a measurement. The RAW
    pricing block is recorded verbatim in the results file so the
    arithmetic can be re-checked by someone who does not trust ours -
    OpenRouter quotes USD per token, and we convert to per-million to
    match config.PRICE_IN/PRICE_OUT.
    """
    url = config.BASE_URL.rstrip("/") + "/models"
    with urllib.request.urlopen(url, timeout=timeout) as r:
        payload = json.load(r)
    for row in payload.get("data", []):
        if row.get("id") == model:
            p = row.get("pricing") or {}
            return {"raw": p,
                    "in_per_million": float(p.get("prompt", 0)) * 1e6,
                    "out_per_million": float(p.get("completion", 0)) * 1e6,
                    "fetched_at": datetime.datetime.now().isoformat(
                        timespec="seconds")}
    return None


# =====================================================================
# RUNTIME CONFIG — the only place config is mutated
# =====================================================================
def apply_runtime_config(entry, key, run_id, dry_run):
    """Mutate the config MODULE, never the config FILE.

    This is the design decision the whole provenance layer rests on. If
    each member edited config.py to set their model, then: the worktree
    would be dirty by construction so "refuse if dirty" could never fire,
    config.py's hash would differ per member so it could not be pinned,
    and six people would be editing the same three lines. Mutating in
    memory costs nothing - every consumer reads these attributes at call
    time - and it buys all three back.
    """
    config.RUNTIME_OVERRIDE = True          # mute the stale-bytecode banner
    config.BACKEND = "scripted" if dry_run else "live"
    config.MODEL = entry["model"]
    config.PROMPT_VERSION = entry["prompt_version"]
    if entry.get("price_in") is not None:
        config.PRICE_IN = float(entry["price_in"])
    if entry.get("price_out") is not None:
        config.PRICE_OUT = float(entry["price_out"])
    config.ALLOW_REASONING = bool(entry.get("reasoning_model"))
    # Per-run, from the roster - never from config.py, so the shipped
    # default stays 0 and D3(b)'s GR-06 keeps asserting the hard stop.
    config.DUPLICATE_RECOVERY_RETRIES = int(
        entry.get("duplicate_recovery_retries") or 0)
    config.set_api_key(key)

    # A PER-RUN LEDGER. logs/decisions.jsonl is git-tracked and every run
    # appends to it; six members sharing it means merge conflicts on an
    # append-only file and six indistinguishable ledgers. This is a module
    # global read at call time, so no source change is needed.
    tools.DECISION_LOG_PATH = os.path.join(
        ROOT, "logs", "battery", "decisions__%s__%s.jsonl"
        % (entry["member"], run_id))


def assert_invariants(roster, entry, dry_run):
    """Re-assert AFTER the mutation, so a typo above fails loudly."""
    bad = []
    for name, want in (roster.get("invariants") or {}).items():
        got = getattr(config, name, None)
        if got != want:
            bad.append("%s is %r, roster says %r" % (name, got, want))
    if config.MODEL != entry["model"]:
        bad.append("MODEL is %r, roster says %r" % (config.MODEL, entry["model"]))
    if config.PROMPT_VERSION != entry["prompt_version"]:
        bad.append("PROMPT_VERSION is %r, roster says %r"
                   % (config.PROMPT_VERSION, entry["prompt_version"]))
    want_backend = "scripted" if dry_run else "live"
    if config.BACKEND != want_backend:
        bad.append("BACKEND is %r, expected %r" % (config.BACKEND, want_backend))
    if bad:
        raise SystemExit("\n  RUNTIME CONFIG IS WRONG:\n    "
                         + "\n    ".join(bad))


# =====================================================================
# THE TRIAL WRAPPER — isolation, spend, reasoning
# =====================================================================
class Budget(object):
    """A battery-level dollar cap on MEASURED spend.

    MAX_TOKENS_PER_RUN is not a spend control: it is per-run and it fires
    only after the tokens are billed. Sixty runs at that ceiling is far
    more money than anyone intends to spend. This is checked against real
    accumulated cost after every trial, and it halts rather than warns.
    """

    def __init__(self, cap_usd, spent=0.0):
        self.cap, self.spent, self.halted = float(cap_usd), float(spent), None

    def add(self, usd):
        self.spent += float(usd or 0.0)

    def exceeded(self):
        return self.spent > self.cap


class BatteryHalt(Exception):
    pass


# =====================================================================
# PROGRESS — because a silent hour looks exactly like a hung process
# =====================================================================
class Progress:
    """One line per graded trial, printed as it lands.

    THIS IS NOT DECORATION. The first live battery on this repository was
    interrupted by hand because sixty trials produced no output between
    the confirmation prompt and the summary, and a run that prints
    nothing for several minutes is indistinguishable from one that has
    hung on a socket. The operator killed a paid run to find out.

    What each line has to answer, in the order you ask it at 2am:
      am I moving · which case · did it pass · what did it cost ·
      how much have I spent · how much longer.

    Nothing here can leak a key: it reads only the graded record.
    """

    def __init__(self, total, already_done, cap, dry_run):
        self.total = total
        self.done = already_done
        self.cap = cap
        self.dry_run = dry_run
        self.started = time.time()
        self.passed = 0
        self.spent = 0.0
        if already_done:
            print("  resuming at trial %d of %d - already-done trials are not "
                  "re-paid for\n" % (already_done, total))
        print("  %-5s %-12s %-4s %-5s %-6s %-9s %-10s %s"
              % ("#", "case", "trial", "check", "turns", "tokens", "US$",
                 "decision"))
        print("  " + "-" * 76)

    def on_result(self, r):
        self.done += 1
        rec = r.get("record") or {}
        self.passed += 1 if r.get("passed") else 0
        self.spent += float(rec.get("cost_usd") or 0.0)

        stopped = rec.get("stopped_by")
        decision = rec.get("decision") or "?"
        if stopped:
            decision = "%s [%s]" % (decision, stopped)

        print("  %-5s %-12s %-4s %-5s %-6s %-9s %-10s %s"
              % ("%d/%d" % (self.done, self.total),
                 r.get("case_id", "?"),
                 "t%s" % r.get("trial", "?"),
                 "PASS" if r.get("passed") else "FAIL",
                 rec.get("turns", "?"),
                 "%.1fk/%.0f" % ((rec.get("tokens_in") or 0) / 1000.0,
                                 rec.get("tokens_out") or 0),
                 "%.5f" % (rec.get("cost_usd") or 0.0),
                 decision[:34]))

        # A FAILED TRIAL SAYS WHY, ONCE. Reading sixty of these after the
        # fact tells you far less than seeing the first one arrive.
        if not r.get("passed"):
            for f in (r.get("fails") or [])[:1]:
                print("        why: %s" % str(f)[:70])

        # The running total, often enough to be useful and rarely enough
        # to stay readable.
        if self.done % 10 == 0 or self.done == self.total:
            elapsed = time.time() - self.started
            rate = elapsed / max(1, self.done - 0)
            left = max(0, self.total - self.done)
            print("        %d/%d done · %d passed (%.0f%%) · US$%.4f of "
                  "US$%.2f%s · ~%s left"
                  % (self.done, self.total, self.passed,
                     100.0 * self.passed / max(1, self.done),
                     self.spent, self.cap,
                     "  [DRY RUN - no money moved]" if self.dry_run else "",
                     _hms(rate * left)))


def _hms(seconds):
    seconds = int(max(0, seconds))
    if seconds < 60:
        return "%ds" % seconds
    if seconds < 3600:
        return "%dm %02ds" % (seconds // 60, seconds % 60)
    return "%dh %02dm" % (seconds // 3600, (seconds % 3600) // 60)


def make_run_one(budget, entry, canary_out_per_turn, on_halt):
    """Wrap run_case with the three things a live battery needs and the
    scripted one does not: exception isolation, spend accounting, and
    reasoning detection."""

    def run_one(case_id, problem=None, verbose=False):
        from loop_agent import run_case
        try:
            record = run_case(case_id, problem=problem, verbose=verbose)
        except backends.LiveFatalError:
            raise
        except Exception as err:                       # noqa: BLE001
            # One trial failing must not end the battery. Record it as a
            # failed trial carrying its error, and carry on.
            record = {"decision": "escalate",
                      "reason": "run raised %s: %s" % (type(err).__name__, err),
                      "case_id": case_id, "evidence": [], "turns": 0,
                      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
                      "turn_tokens": [], "guardrails_fired": [],
                      "stopped_by": "exception", "backend": config.BACKEND}

        budget.add(record.get("cost_usd"))
        spike = detect_reasoning(record, canary_out_per_turn)
        if spike:
            on_halt("reasoning", spike)
            raise BatteryHalt(spike)
        if budget.exceeded():
            msg = ("measured spend US$%.4f exceeds the cap of US$%.2f"
                   % (budget.spent, budget.cap))
            on_halt("max_spend", msg)
            raise BatteryHalt(msg)
        return record

    return run_one


def detect_reasoning(record, baseline_out_per_turn):
    """A reasoning model bought by accident, caught from the record.

    Hidden thinking bills as OUTPUT, at 4-5x input. `reasoning: exclude`
    hides the tokens and still charges for them, so telemetry after the
    fact is not a control - this halts.
    """
    for usage in record.get("turn_usage") or []:
        details = (usage.get("usage") or {}).get("completion_tokens_details") or {}
        if int(details.get("reasoning_tokens") or 0) > 0:
            return ("the provider reported %s reasoning tokens - this is a "
                    "reasoning model and it bills them as output"
                    % details["reasoning_tokens"])
    outs = [to for _, to in record.get("turn_tokens") or []]
    if outs and baseline_out_per_turn:
        worst = max(outs)
        if worst > max(8 * baseline_out_per_turn, 4000):
            return ("output tokens spiked to %d on one turn against a canary "
                    "baseline of %d - that is the shape of hidden reasoning"
                    % (worst, baseline_out_per_turn))
    return None


# =====================================================================
# AGGREGATION
# =====================================================================
def aggregate(results, key):
    """The numbers the report table needs - and TWO negative rates.

    The negative TRIAL rate and the negative 3-OF-3 rate are different
    findings. A model at 90% trial / 70% three-of-three is unreliable on
    refusals; one at 90%/90% is consistently wrong about one case. The
    3x trial policy exists to tell those apart, and reporting only the
    trial rate throws away the whole reason for tripling their cost.
    """
    graded = [r for r in results
              if (r["record"].get("stopped_by") != "transport")]
    transport = [r for r in results
                 if r["record"].get("stopped_by") == "transport"]

    def is_neg(r):
        return harness.is_negative(key.get(r["case_id"]))

    neg = [r for r in graded if is_neg(r)]
    ordi = [r for r in graded if not is_neg(r)]

    by_case = {}
    for r in neg:
        by_case.setdefault(r["case_id"], []).append(r["passed"])
    three_of_three = sum(1 for v in by_case.values() if all(v))

    turns = [r["record"]["turns"] for r in graded] or [0]
    stopped = {}
    for r in graded:
        s = r["record"].get("stopped_by")
        if s:
            stopped[s] = stopped.get(s, 0) + 1

    rate = lambda rs: (sum(1 for r in rs if r["passed"]) / len(rs)) if rs else 0.0
    return {
        "trials_planned": len(results),
        "trials_graded": len(graded),
        "trials_transport_failed": len(transport),
        "passed": sum(1 for r in graded if r["passed"]),
        "pass_rate": rate(graded),
        "ordinary": {"trials": len(ordi), "rate": rate(ordi)},
        "negative": {"trials": len(neg), "rate": rate(neg),
                     "cases": len(by_case), "cases_3of3": three_of_three,
                     "consistency": (three_of_three / len(by_case))
                                    if by_case else 0.0},
        "median_turns": statistics.median(turns),
        "max_turns": max(turns),
        "stopped_by": stopped,
        "tokens_in": sum(r["record"].get("tokens_in") or 0 for r in results),
        "tokens_out": sum(r["record"].get("tokens_out") or 0 for r in results),
        "cost_usd": sum(r["record"].get("cost_usd") or 0.0 for r in results),
        "usage_complete": all(r["record"].get("usage_complete", True)
                              for r in results),
        "served_models": sorted({r["record"].get("served_model")
                                 for r in results
                                 if r["record"].get("served_model")}),
    }


# =====================================================================
# PRE-FLIGHT
# =====================================================================
def preflight_banner(entry, fp, roster, checkpoint, price, budget, dry_run):
    shape = fp["plan_shape"]
    done = len(checkpoint.done())
    print()
    print("=" * 70)
    print("  D5(b) LIVE BATTERY" + ("  [DRY RUN - scripted, no network, no cost]"
                                    if dry_run else
                                    "  - THIS SPENDS REAL MONEY ON YOUR KEY"))
    print("=" * 70)
    print("  member          %s  (%s)" % (entry["member"], entry.get("full_name", "")))
    print("  model           %s" % entry["model"])
    print("  family / tier   %s / %s" % (entry.get("family"), entry.get("tier")))
    print("  prompt version  %s   sha %s   (v1 %s, v2 %s - they differ %s)"
          % (entry["prompt_version"],
             prov.short(fp["prompt_sha256"][entry["prompt_version"]]),
             prov.short(fp["prompt_sha256"]["v1"]),
             prov.short(fp["prompt_sha256"]["v2"]),
             "YES" if fp["prompt_sha256"]["v1"] != fp["prompt_sha256"]["v2"]
             else "NO !!"))
    print("  commit          %s   worktree %s"
          % (prov.short(fp["commit"]),
             "clean" if not fp["dirty"] else "DIRTY (%d files)" % len(fp["dirty"])))
    print("  answer key      %d cases, %d negative   sha %s"
          % (shape["cases"], shape["negative"], prov.short(fp["answer_key_sha256"])))
    print("  plan            %d trials (%d ordinary x1 + %d negative x3)  sha %s"
          % (shape["trials"], shape["ordinary"], shape["negative"],
             prov.short(fp["plan_sha256"])))
    print("                  ^ DERIVED from the fixtures, never typed")
    if price:
        print("  price           in $%.4f/M  out $%.4f/M   fetched %s"
              % (price["in_per_million"], price["out_per_million"],
                 price["fetched_at"]))
    else:
        print("  price           in $%.4f/M  out $%.4f/M   (roster, checked %s)"
              % (config.PRICE_IN, config.PRICE_OUT,
                 entry.get("price_checked_on")))
    print("  spend cap       US$%.2f   halts on MEASURED cost, not an estimate"
          % budget.cap)
    print("  checkpoint      %s" % os.path.relpath(checkpoint.path, ROOT))
    print("  resuming        %s"
          % ("no (0 done)" if not done
             else "YES - %d of %d already done, US$%.4f already spent"
                  % (done, shape["trials"], checkpoint.spend_usd())))
    for w in checkpoint.warnings:
        print("  NOTE            %s" % w)
    print()


def confirm(expected):
    got = input("  Type the model id to proceed (anything else aborts): ").strip()
    if got != expected:
        print("  Aborted. Nothing was run and nothing was spent.")
        return False
    return True


# =====================================================================
# MAIN
# =====================================================================
def main(argv=None):
    ap = argparse.ArgumentParser(prog="run_battery.py")
    ap.add_argument("--member")
    ap.add_argument("--roster", default=prov.ROSTER_PATH)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-drift", action="store_true")
    ap.add_argument("--freeze", action="store_true",
                    help="write the current hashes into the roster's "
                         "`expected` block. Run ONCE, at the frozen commit.")
    ap.add_argument("--retry-errors", action="store_true")
    ap.add_argument("--max-spend", type=float)
    ap.add_argument("--no-canary", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--force-unlock", action="store_true")
    ap.add_argument("--override", action="append", default=[],
                    metavar="CHECK=reason")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)

    roster = prov.load_roster(args.roster)

    # ---- --freeze: stamp the hashes, then stop -----------------------
    if args.freeze:
        fp = prov.fingerprint(roster.get("problem"))
        roster["expected"] = {
            "_note": roster.get("expected", {}).get("_note", ""),
            "answer_key_sha256": fp["answer_key_sha256"],
            "fixtures_sha256": fp["fixtures_sha256"],
            "plan_sha256": fp["plan_sha256"],
            "prompt_sha256": fp["prompt_sha256"],
            "sources_sha256": fp["sources_sha256"]}
        roster["trials_expected"] = fp["plan_shape"]["trials"]
        with open(args.roster, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("\n  Froze the roster at commit %s." % prov.short(fp["commit"]))
        print("  trials_expected = %d (derived)" % fp["plan_shape"]["trials"])
        print("  Commit this, cut the tag, and nobody runs until their HEAD "
              "matches.\n")
        return 0

    # ---- roster structure, before anything else ----------------------
    errs = prov.validate_roster(roster)
    if args.dry_run:
        # A dry run spends nothing, so an unfilled roster is a warning
        # rather than a refusal - the point is to exercise the machinery.
        soft = ("placeholder", "price_checked_on", "price last checked")
        errs = [e for e in errs if not any(s in e for s in soft)]
    if errs:
        print("\n  THE ROSTER IS NOT VALID. Nothing was run.\n")
        for e in errs:
            print("    - %s" % e)
        print()
        return 2

    if not args.member:
        print("\n  --member is required. Known members: %s\n"
              % ", ".join(m["member"] for m in roster["members"]))
        return 2

    entry = prov.member_entry(roster, args.member)
    fp = prov.fingerprint(roster.get("problem"))
    rid = prov.run_id(fp, entry)

    # ---- drift -------------------------------------------------------
    overrides = {}
    for spec in args.override:
        name, _, reason = spec.partition("=")
        if not reason.strip():
            print("  --override needs a reason: --override %s=\"why\"" % name)
            return 2
        overrides[name.strip()] = reason.strip()

    violations = prov.check_drift(fp, roster, entry)
    if args.allow_dirty:
        overrides.setdefault("worktree_clean", "--allow-dirty")
        violations = [x for x in violations if x.check != "worktree_clean"]
    if args.dry_run:
        # A dry run spends nothing and its output never enters the
        # six-way comparison, so "you are not at the frozen commit" is
        # information rather than an obstacle. Everything ELSE - the
        # prompt hashes, the roster structure, the derived trial count -
        # still blocks, because those are what the dry run exists to
        # rehearse.
        for x in violations:
            if x.check in ("commit", "worktree_clean"):
                print("  dry run, so not blocking on: %s (%s)"
                      % (x.check, x.actual))
        violations = [x for x in violations
                      if x.check not in ("commit", "worktree_clean")]

    blocking = []
    for x in violations:
        if x.check in overrides and x.check not in prov.UNOVERRIDABLE:
            print("  OVERRIDDEN: %s - %s" % (x.check, overrides[x.check]))
        else:
            blocking.append(x)

    if args.verify_drift:
        print("\n  FINGERPRINT for %s (paste this in the group chat)\n" % entry["member"])
        for k in ("commit", "answer_key_sha256", "fixtures_sha256",
                  "plan_sha256"):
            print("    %-20s %s" % (k, prov.short(fp[k]) if k != "commit"
                                    else prov.short(fp[k])))
        print("    %-20s v1=%s v2=%s" % ("prompt_sha256",
                                         prov.short(fp["prompt_sha256"]["v1"]),
                                         prov.short(fp["prompt_sha256"]["v2"])))
        print("    %-20s %s" % ("plan_shape", fp["plan_shape"]))
        print("    %-20s %s" % ("run_id", rid))
        print()
        if blocking:
            print("  %d blocking violation(s):" % len(blocking))
            for x in blocking:
                print(x)
            print()
            return 2
        print("  No drift. This machine is comparable with the others.\n")
        return 0

    if blocking:
        print("\n  REFUSING TO RUN - this battery would not be comparable "
              "with the others.\n")
        for x in blocking:
            print(x)
            if x.check in prov.UNOVERRIDABLE:
                print("      (this one cannot be overridden - it means the "
                      "run would measure nothing)")
        print()
        return 2

    # ---- key, config, checkpoint -------------------------------------
    key = obtain_key(args.dry_run)
    restore_hook = install_scrubbing_excepthook(key)
    apply_runtime_config(entry, key, rid, args.dry_run)
    assert_invariants(roster, entry, args.dry_run)

    price = None
    if not args.dry_run:
        try:
            price = fetch_price(entry["model"])
            if price:
                config.PRICE_IN = price["in_per_million"]
                config.PRICE_OUT = price["out_per_million"]
        except Exception as err:                        # noqa: BLE001
            print("  NOTE: could not fetch live pricing (%s). Falling back to "
                  "the roster's figures, which were checked on %s."
                  % (err, entry.get("price_checked_on")))

    header = {"run_id": rid, "member": entry["member"],
              "model": entry["model"], "prompt_version": entry["prompt_version"],
              "tier": entry.get("tier"), "family": entry.get("family"),
              "dry_run": args.dry_run, "fingerprint": fp,
              "price_in": config.PRICE_IN, "price_out": config.PRICE_OUT,
              "started": datetime.datetime.now().isoformat(timespec="seconds")}
    path = ckpt.path_for(ROOT, entry["member"], rid, dry_run=args.dry_run)
    try:
        checkpoint = ckpt.Checkpoint.open(path, header)
    except ckpt.CheckpointConflict as err:
        print("\n  %s\n" % err)
        return 2
    try:
        checkpoint.lock(force=args.force_unlock)
    except ckpt.Locked as err:
        print("\n  %s\n" % err)
        return 2
    if args.force_unlock:
        checkpoint.append({"kind": "override", "check": "lock",
                           "reason": "--force-unlock"})
    for name, reason in overrides.items():
        checkpoint.append({"kind": "override", "check": name, "reason": reason})

    cap = args.max_spend or entry.get("max_spend_usd") or 1.0
    budget = Budget(cap, spent=checkpoint.spend_usd())

    try:
        preflight_banner(entry, fp, roster, checkpoint, price, budget,
                         args.dry_run)
        if not args.dry_run and not confirm(entry["model"]):
            return 1

        skip = set(checkpoint.done())
        if args.retry_errors:
            skip -= checkpoint.errored()

        def on_halt(why, detail):
            checkpoint.append({"kind": "halt", "why": why, "detail": detail})
            print("\n  HALTED (%s): %s" % (why, detail))
            print("  Progress is checkpointed. Re-run with --member %s to "
                  "resume.\n" % entry["member"])

        baseline = None
        if not args.dry_run and not args.no_canary:
            baseline = run_canary(entry, budget, on_halt)
            if baseline is None:
                return 1

        run_one = make_run_one(budget, entry, baseline, on_halt)
        plan_cases = []
        for cid, _t in prov.build_plan(roster.get("problem")):
            if cid not in plan_cases:
                plan_cases.append(cid)
        if args.limit:
            plan_cases = plan_cases[:args.limit]

        results = list(checkpoint.results())
        progress = Progress(fp["plan_shape"]["trials"], len(results),
                            budget.cap, args.dry_run)

        def on_result(r):
            # Checkpoint FIRST, then print. If the process dies between
            # the two, the trial is still paid for and still recorded;
            # printing first and crashing would lose it.
            checkpoint.append(dict(r, kind="trial"))
            progress.on_result(r)

        try:
            fresh, queue = harness.run_set(
                plan_cases, problem=roster.get("problem"),
                run_one=run_one, skip=skip, on_result=on_result)
            results += fresh
        except BatteryHalt:
            results = list(checkpoint.results())
            queue = []
        except backends.LiveFatalError as err:
            checkpoint.append({"kind": "halt", "why": "fatal",
                               "detail": str(err)})
            print("\n  FATAL - the battery stopped immediately rather than "
                  "retrying 60 times:\n    %s\n" % err)
            return 3

        key_rows = harness.load_key(roster.get("problem"))
        summary = aggregate(results, key_rows)
        out = write_results(entry, fp, rid, header, results, queue, summary,
                            price, overrides, args.dry_run, key)
        checkpoint.append({"kind": "footer", "completed": len(results),
                           "cost_usd": summary["cost_usd"]})
        print_summary(summary, out)
        return 0
    finally:
        checkpoint.unlock()
        checkpoint.close()
        sys.excepthook = restore_hook


def run_canary(entry, budget, on_halt):
    """One live run, on THREE case shapes, before committing to sixty.

    The estimate that matters is measured, not assumed - and it is
    measured on the worst shape, not a convenient one. An escalation
    exits in two turns; a four-line approval with a pre-authorisation to
    chase runs five. Pricing a battery off the cheap shape and a flat
    headroom percentage is a number chosen for reassurance.
    """
    from loop_agent import run_case
    print("  CANARY - one live run each on three case shapes, so the "
          "estimate is measured.")
    shapes = pick_canary_cases()
    trials = prov.plan_shape(config.PROBLEM)["trials"]
    worst_out, costs = 0, []
    for label, cid in shapes:
        try:
            rec = run_case(cid, problem=config.PROBLEM)
        except backends.LiveFatalError as err:
            print("\n  FATAL on the canary - stopping before the battery:\n"
                  "    %s\n" % err)
            return None
        outs = [to for _, to in rec.get("turn_tokens") or []] or [0]
        worst_out = max(worst_out, max(outs))
        cost = rec.get("cost_usd") or 0.0
        costs.append(cost)
        budget.add(cost)
        print("    %-10s %-12s %d turns  %d in / %d out  US$%.5f  -> %s"
              % (label, cid, rec["turns"], rec["tokens_in"], rec["tokens_out"],
                 cost, rec.get("decision")))
    mean, worst = sum(costs) / max(1, len(costs)), max(costs or [0.0])
    print("\n    measured mean US$%.5f/run · WORST shape US$%.5f" % (mean, worst))
    print("    projected battery US$%.4f at the mean, US$%.4f at the worst"
          % (mean * trials, worst * trials))
    print("    cap US$%.2f · US$%.5f already spent on the canary"
          % (budget.cap, budget.spent))
    if worst * trials > budget.cap:
        print("    ^ the WORST-SHAPE projection exceeds your cap. The battery "
              "will halt partway unless you raise --max-spend.")
    if input("\n  Proceed with the full battery? Type yes: ").strip() != "yes":
        print("  Aborted after the canary. You spent US$%.5f." % budget.spent)
        return None
    return max(1, worst_out)


def pick_canary_cases():
    """An ordinary approve, an escalate, and the longest run in the set."""
    key = harness.load_key(config.PROBLEM)
    cases = [c for c in harness.load_cases(config.PROBLEM) if c in key]
    approve = next((c for c in cases
                    if key[c]["expected_decision"] == "approve_in_principle"), None)
    esc = next((c for c in cases if key[c]["expected_decision"] == "escalate"), None)
    longest = max(cases, key=lambda c: len(key[c].get("must_record") or []))
    picked, seen = [], set()
    for label, cid in (("approve", approve), ("escalate", esc),
                       ("longest", longest)):
        if cid and cid not in seen:
            picked.append((label, cid))
            seen.add(cid)
    return picked


def write_results(entry, fp, rid, header, results, queue, summary, price,
                  overrides, dry_run, key):
    os.makedirs(LIVE_DIR, exist_ok=True)
    # Model ids carry "/" and ":" and, before the roster is filled, angle
    # brackets and spaces. A filename is not the place to find that out.
    slug = "".join(c if (c.isalnum() or c in "-._") else "-"
                   for c in entry["model"]).strip("-")
    name = ("battery__%s__%s__%s__%s__%s%s.json"
            % (entry["member"], slug, entry["prompt_version"],
               datetime.date.today().isoformat(), rid,
               "__OVERRIDE" if overrides else ""))
    out = os.path.join(LIVE_DIR, "dryrun" if dry_run else "", name)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    payload = {
        "schema": 1, "dry_run": dry_run, "clean": not overrides,
        "member": entry["member"], "full_name": entry.get("full_name"),
        "model": entry["model"], "family": entry.get("family"),
        "tier": entry.get("tier"), "prompt_version": entry["prompt_version"],
        "problem": fp["problem"], "backend": config.BACKEND,
        "run_id": rid, "commit": fp["commit"],
        "date": datetime.date.today().isoformat(),
        "started": header["started"],
        "ended": datetime.datetime.now().isoformat(timespec="seconds"),
        "python": fp["python"],
        "fingerprint": fp,
        "prices": {"in_per_million": config.PRICE_IN,
                   "out_per_million": config.PRICE_OUT,
                   "live": price,
                   "roster_checked_on": entry.get("price_checked_on"),
                   "source": entry.get("price_source_url")},
        "overrides": [{"check": k, "reason": v} for k, v in overrides.items()],
        "summary": summary,
        "results": results,
        "judgement_queue": queue,
    }
    text = json.dumps(payload, indent=2, default=str)
    assert_no_secret(text, key)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return out


def print_summary(s, out):
    n = s["negative"]
    print()
    print("=" * 70)
    print("  %d of %d graded trials passed   (%.1f%%)"
          % (s["passed"], s["trials_graded"], 100 * s["pass_rate"]))
    print("=" * 70)
    print("  ordinary            %d trials, %.1f%%"
          % (s["ordinary"]["trials"], 100 * s["ordinary"]["rate"]))
    print("  negative (trials)   %d trials, %.1f%%"
          % (n["trials"], 100 * n["rate"]))
    print("  negative (3 of 3)   %d of %d cases passed all three  (%.1f%%)"
          % (n["cases_3of3"], n["cases"], 100 * n["consistency"]))
    print("                      ^ the number the 3x policy exists to produce")
    if s["trials_transport_failed"]:
        print("  transport failures  %d  (excluded from the denominator - a "
              "network problem is not evidence about a model)"
              % s["trials_transport_failed"])
    print("  median turns        %s      max %s"
          % (s["median_turns"], s["max_turns"]))
    print("  tokens              %d in / %d out%s"
          % (s["tokens_in"], s["tokens_out"],
             "" if s["usage_complete"] else "   (INCOMPLETE - lower bound)"))
    print("  measured cost       US$%.4f" % s["cost_usd"])
    if s["stopped_by"]:
        print("  stopped by          %s" % s["stopped_by"])
    print()
    print("  Wrote %s" % os.path.relpath(out, ROOT))
    print()


if __name__ == "__main__":
    sys.exit(main())
