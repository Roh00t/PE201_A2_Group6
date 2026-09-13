#!/usr/bin/env python3
"""
PE6201 · A2 — RE-VERIFY THE ROSTER AGAINST OPENROUTER  (D5b)
====================================================================
    python3 evals/check_roster_prices.py            # check
    python3 evals/check_roster_prices.py --update   # check and rewrite

Free. A public GET against https://openrouter.ai/api/v1/models. No key,
no tokens, no cost.

WHY THIS EXISTS. The brief requires prices "verified on the day, with the
date recorded", and validate_roster() refuses a price_checked_on older
than 14 days. That is a rule nobody can satisfy by hand for six models
the night before a deadline, so it is one command instead.

IT ALSO CHECKS THE MODEL IDS EXIST. When this roster was first drafted,
two of the six ids we had been given were not on OpenRouter at all -
'google/gemini-flash-1.5' and 'anthropic/claude-3.5-haiku'. Either one
would have raised LiveFatalError on the FIRST call of a paid run, after
the confirmation prompt and after the key was entered. A model id is
worth checking for free before it is worth 60 trials.

WHAT IT WILL NOT DO. It will not silently rewrite a price. Without
--update it only reports, because a price that moved is a decision - the
tier may have changed, and with it whether the battery still fits the
US$3 ceiling.
====================================================================
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals import battery_provenance as prov        # noqa: E402

MODELS_URL = "https://openrouter.ai/api/v1/models"

# Tier boundaries, in US$ for one 60-trial battery on OUR measured
# tokens. Assigning a tier by vendor reputation is how a "cheap" model
# turns out to cost more than a mid one; assigning it by measured cost
# cannot.
#
# ANCHORED ON THE BRIEF, NOT ON A ROUND NUMBER. Section 7's three reference
# prices cost, on our tokens: cheap 0.10/0.40 -> $0.148, mid 1.00/5.00 ->
# $1.579, frontier 5.00/25.00 -> $7.896. The edges sit at the geometric
# midpoints: sqrt(0.148 * 1.579) = $0.48, and the mid ceiling is the US$3
# per-member cap itself - so "frontier" and "refused by the runner" are
# the same set.
#
# The previous bands (cheap <= $0.20, mid <= $1.00) classified the brief's
# OWN mid-tier reference price as frontier. Corrected 2026-09-13.
TIER_BANDS = (("free", 0.0), ("cheap", 0.48), ("mid", 3.00),
              ("frontier", float("inf")))


def measured_tokens():
    """Per-battery tokens from our own committed scripted run."""
    import glob
    files = sorted(glob.glob(os.path.join(ROOT, "results", "scripted",
                                          "problemA__scripted__*.json")))
    if not files:
        raise SystemExit("  No scripted run to price against. "
                         "Run `python3 run_eval.py` first - it is free.")
    with open(files[-1], encoding="utf-8") as fh:
        doc = json.load(fh)
    rows = doc["results"]
    return (sum(r["record"]["tokens_in"] for r in rows),
            sum(r["record"]["tokens_out"] for r in rows), len(rows))


def fetch_prices():
    req = urllib.request.Request(MODELS_URL, headers={"User-Agent": "PE6201-A2"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise SystemExit("\n  Could not reach OpenRouter: %s\n"
                         "  Nothing was changed.\n" % err)
    return {m["id"]: (float(m["pricing"]["prompt"]) * 1e6,
                      float(m["pricing"]["completion"]) * 1e6)
            for m in data.get("data", [])
            if m.get("pricing", {}).get("prompt") is not None}


def tier_for(cost):
    for name, ceiling in TIER_BANDS:
        if cost <= ceiling:
            return name
    return "frontier"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check_roster_prices.py")
    ap.add_argument("--update", action="store_true",
                    help="rewrite prices, tiers and price_checked_on")
    ap.add_argument("--roster", default=prov.ROSTER_PATH)
    ap.add_argument("--output-factor", type=float, default=3.0)
    args = ap.parse_args(argv)

    roster = prov.load_roster(args.roster)
    live = fetch_prices()
    t_in, t_out, trials = measured_tokens()
    today = datetime.date.today().isoformat()

    print()
    print("=" * 78)
    print("  ROSTER vs OPENROUTER, %s" % today)
    print("=" * 78)
    print("  priced on %d measured trials: %s in / %s out tokens (x%g on output)"
          % (trials, "{:,}".format(t_in), "{:,}".format(t_out),
             args.output_factor))
    print("  %d models listed by OpenRouter right now" % len(live))
    print()

    problems, changes, total = [], [], 0.0
    print("  %-12s %-42s %-15s %8s %s"
          % ("member", "model", "live in/out", "battery", "status"))
    print("  " + "-" * 92)

    for m in roster.get("members", []):
        model = m.get("model", "")
        if model not in live:
            print("  %-12s %-42s %-15s %8s %s"
                  % (m["member"], model, "-", "-", "MODEL NOT ON OPENROUTER"))
            problems.append("%s: %r is not a model OpenRouter serves. It would "
                            "raise LiveFatalError on the first paid call."
                            % (m["member"], model))
            continue

        pin, pout = live[model]
        cost = (t_in * pin + t_out * args.output_factor * pout) / 1e6
        total += cost
        want_tier = tier_for(cost)

        notes = []
        if m.get("price_in") is None or abs(m["price_in"] - pin) > 1e-9:
            notes.append("price_in %s -> %s" % (m.get("price_in"), round(pin, 6)))
        if m.get("price_out") is None or abs(m["price_out"] - pout) > 1e-9:
            notes.append("price_out %s -> %s" % (m.get("price_out"), round(pout, 6)))
        if m.get("tier") != want_tier:
            notes.append("tier %s -> %s" % (m.get("tier"), want_tier))
        if cost > 3.0:
            problems.append("%s: %s costs US$%.2f, over the US$3 per-member "
                            "ceiling. run_live_battery.py will refuse it."
                            % (m["member"], model, cost))

        status = "OK" if not notes else "; ".join(notes)
        print("  %-12s %-42s %-15s %8s %s"
              % (m["member"], model, "$%.3f/$%.3f" % (pin, pout),
                 "$%.4f" % cost, status))

        if notes:
            changes.append((m, pin, pout, want_tier, round(cost, 4)))

    print("  " + "-" * 92)
    print("  %-52s TEAM TOTAL  $%.4f" % ("", total))
    print()

    if problems:
        print("  PROBLEMS THAT WOULD COST MONEY OR REFUSE A RUN:")
        for p in problems:
            print("    ! %s" % p)
        print()

    if not changes and not problems:
        print("  Every price and tier matches OpenRouter today.")
        stale = [m["member"] for m in roster.get("members", [])
                 if m.get("price_checked_on") != today]
        if stale and args.update:
            pass
        elif stale:
            print("  %d row(s) still carry an older price_checked_on. Re-run"
                  % len(stale))
            print("  with --update to stamp today's date.")
        print()

    if args.update:
        for m, pin, pout, tier, cost in changes:
            m["price_in"], m["price_out"] = round(pin, 6), round(pout, 6)
            m["tier"] = tier
            m["estimated_battery_usd"] = cost
        for m in roster.get("members", []):
            if m.get("model") in live:
                m["price_checked_on"] = today
                m["price_source_url"] = MODELS_URL
                m.setdefault("estimated_battery_usd", 0.0)
        with open(args.roster, "w", encoding="utf-8") as fh:
            json.dump(roster, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("  Updated %s (%d row(s) changed, dates stamped %s)."
              % (os.path.relpath(args.roster, ROOT), len(changes), today))
        errs = prov.validate_roster(roster)
        print("  validate_roster: %s\n"
              % ("still valid" if not errs else "NOW INVALID - %s" % errs))
    elif changes:
        print("  Nothing was changed. Re-run with --update to apply, but read")
        print("  the tier column first: a model that moved band may no longer")
        print("  belong to the member holding it.")
        print()

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
