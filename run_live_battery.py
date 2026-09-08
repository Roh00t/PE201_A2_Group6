#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PE6201 · A2 — THE FRIENDLY FRONT DOOR TO THE LIVE BATTERY  (D5b)
双语实盘评测启动器
====================================================================
    python3 run_live_battery.py --name "Zhao Yujia"
    python3 run_live_battery.py --name yujia --dry-run
    python3 run_live_battery.py                 # asks for your name

WHAT THIS IS, AND WHAT IT IS NOT.

This is a WRAPPER. It does not run the battery itself and it does not
grade anything. It resolves your name to your roster row, prices the
run against MEASURED tokens, refuses if that price breaks the US$3
per-member ceiling, and then hands control to evals/run_battery.py -
which owns provenance, drift refusal, checkpointing, the spend cap and
every line of the key handling.

Rebuilding any of that here would have been the wrong move twice over:
the fingerprint that makes six members' runs comparable lives in
run_battery, and so does the rule that the key is never written down.
A second runner is a second set of numbers nobody can reconcile.

--------------------------------------------------------------------
WHY THE ESTIMATE IS OUR OWN NUMBER, NOT THE BRIEF'S

Section 7 of the brief prices a battery at roughly 43,200 input tokens
per run. That is the brief's example agent, not ours. Ours is measured
from the scripted run committed in results/scripted/, where 60 trials
cost 1,083,600 input and 32,400 output tokens - about 18,060 in and 540
out per trial, because D2(c)'s parallel grouping removed 41% of the
turns and with them 53% of the input tokens.

So the estimate below is OUR agent priced at TODAY'S posted price. It
is still an estimate: the scripted transcript is a floor on output
tokens, because a live model writes more prose than a canned move does.
--output-factor exists for exactly that, and defaults to 3.

The number that actually stops the run is not this estimate at all. It
is the MEASURED spend cap inside run_battery, which halts mid-battery
on real billed tokens.
====================================================================
"""
import argparse
import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from evals import battery_provenance as prov          # noqa: E402
from evals import run_battery as battery              # noqa: E402

# ---------------------------------------------------------------------
# THE CEILING. The brief, section 7, verbatim: "If your estimated live
# spend exceeds US$3 per member, your battery is too large - cut trials
# or cases, or move a model down a tier, and say in the report that you
# did, and why."
#
# It is written here as a NUMBER IN CODE rather than a sentence in a
# document, because a budget rule that lives only in prose is a budget
# rule nobody enforces at 2am.
# ---------------------------------------------------------------------
PER_MEMBER_CEILING_USD = 3.00
COURSE_KEY_USD = 10.00

TIER_PRICES = {                      # US$ per million tokens, [brief §7]
    "cheap": (0.10, 0.40),
    "mid": (1.00, 5.00),
    "frontier": (5.00, 25.00),
}


# =====================================================================
# BILINGUAL OUTPUT
# =====================================================================
LANG = "both"


def say(en, zh="", indent="  "):
    """One line, in whichever languages are switched on.

    Half this team reads Chinese faster than English and every one of
    them is about to spend their own money. A confirmation prompt that
    is only half understood is not a confirmation.
    """
    if LANG in ("en", "both") and en:
        print(indent + en)
    if LANG in ("zh", "both") and zh:
        print(indent + zh)


def rule(char="=", n=70):
    print(char * n)


# =====================================================================
# NAME RESOLUTION
# =====================================================================
# The roster keys are short handles. People type their own names, in
# either script, in either order. Refusing "Zhao Yujia" because the
# roster says "yujia" would be the tool being difficult for no reason.
ALIASES = {
    "rohit": ["rohit", "rohit panda", "panda rohit", "panda", "罗希特"],
    "huangyu": ["huangyu", "huang yu", "yu huang", "黄煜", "黄宇"],
    "yunke": ["yunke", "li yunke", "yunke li", "李云可", "李昀可"],
    "yanran": ["yanran", "xia yanran", "yanran xia", "夏嫣然", "夏艳然"],
    "bowen": ["bowen", "shen bowen", "bowen shen", "沈博文"],
    "yujia": ["yujia", "zhao yujia", "yujia zhao", "赵宇佳", "赵雨佳"],
}


def resolve_member(roster, raw):
    """A roster row from whatever the human typed. Never a guess.

    Ambiguity is reported, not resolved silently. Running the wrong
    member's model spends the wrong person's money on a row that is
    already claimed, and the checkpoint would let it.
    """
    if not raw:
        return None
    want = " ".join(str(raw).strip().lower().split())
    members = roster.get("members", [])
    keys = [m.get("member", "") for m in members]

    for m in members:                                   # exact roster key
        if m.get("member", "").lower() == want:
            return m
    for m in members:                                   # exact full name
        if (m.get("full_name") or "").lower() == want:
            return m
    for key, names in ALIASES.items():                  # curated aliases
        if want in names and key in keys:
            return members[keys.index(key)]

    hits = []                                           # single given name
    for m in members:
        parts = (m.get("full_name") or "").lower().split()
        if want in parts or want == m.get("member", "").lower():
            hits.append(m)
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise SystemExit(
            "\n  %r matches more than one member: %s\n"
            "  %r 匹配到多位成员，请用花名册中的简称。\n"
            % (raw, ", ".join(m["member"] for m in hits), raw))
    return None


def ask_for_name(roster):
    say("Who are you? / 你是哪位？", "")
    print()
    for m in roster.get("members", []):
        print("      %-10s %s   (%s, %s tier, prompt %s)"
              % (m.get("member"), m.get("full_name", ""),
                 m.get("family"), m.get("tier"), m.get("prompt_version")))
    print()
    raw = input("  Your name / 你的名字: ").strip()
    entry = resolve_member(roster, raw)
    if entry is None:
        raise SystemExit(
            "\n  Not on the roster: %r. Nothing was run.\n"
            "  花名册中没有 %r。未执行任何操作。\n" % (raw, raw))
    return entry


# =====================================================================
# THE ESTIMATE
# =====================================================================
def measured_token_basis():
    """Per-trial tokens, taken from OUR OWN committed scripted run.

    Returns (tokens_in_per_trial, tokens_out_per_trial, source_file).
    Raises if no scripted run exists - an estimate with no measurement
    behind it is a guess wearing a decimal point, and the whole reason
    D5(a) runs before D5(b) is so this number exists.
    """
    pattern = os.path.join(ROOT, "results", "scripted",
                           "problemA__scripted__*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(
            "\n  No scripted run in results/scripted/, so there is no\n"
            "  measured token basis to price this battery with.\n"
            "  Run `python3 run_eval.py` first - it is free.\n"
            "  请先运行 `python3 run_eval.py`（免费），再来估价。\n")
    path = files[-1]
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    rows = doc.get("results") or []
    if not rows:
        raise SystemExit("  %s has no trials in it." % path)
    t_in = sum(r["record"]["tokens_in"] for r in rows)
    t_out = sum(r["record"]["tokens_out"] for r in rows)
    n = len(rows)
    return t_in / n, t_out / n, os.path.relpath(path, ROOT)


def prices_for(entry):
    """Roster price if it has been verified today; tier list price if not.

    The roster is the truth once someone has checked a vendor page and
    written the date down. Until then we fall back to the brief's tier
    table and SAY SO, rather than quietly pricing a run at zero.
    """
    p_in, p_out = entry.get("price_in"), entry.get("price_out")
    if p_in is not None and p_out is not None:
        return float(p_in), float(p_out), "roster (checked %s)" % (
            entry.get("price_checked_on") or "?")
    tier = (entry.get("tier") or "cheap").lower()
    p_in, p_out = TIER_PRICES.get(tier, TIER_PRICES["cheap"])
    return p_in, p_out, "brief §7 %s-tier list price - NOT yet verified" % tier


def estimate(entry, trials, output_factor):
    t_in, t_out, source = measured_token_basis()
    p_in, p_out = prices_for(entry)[:2]
    total_in = t_in * trials
    total_out = t_out * trials * output_factor
    usd = (total_in * p_in + total_out * p_out) / 1_000_000.0
    return {
        "tokens_in_per_trial": t_in,
        "tokens_out_per_trial": t_out,
        "output_factor": output_factor,
        "total_in": total_in,
        "total_out": total_out,
        "usd": usd,
        "basis": source,
        "price_in": p_in,
        "price_out": p_out,
        "price_source": prices_for(entry)[2],
    }


# =====================================================================
# THE BANNER
# =====================================================================
def banner(entry, shape, est, cap, dry_run):
    print()
    rule()
    if dry_run:
        say("D5(b) LIVE BATTERY — DRY RUN. Scripted, no network, no cost.",
            "D5(b) 实盘评测 —— 演练模式。脚本后端，不联网，不花钱。", "  ")
    else:
        say("D5(b) LIVE BATTERY — THIS SPENDS REAL MONEY ON YOUR OWN KEY.",
            "D5(b) 实盘评测 —— 这会花掉你自己 API Key 里的真钱。", "  ")
    rule()
    print("  member / 成员        %s  (%s)"
          % (entry["member"], entry.get("full_name", "")))
    print("  model / 模型         %s" % entry["model"])
    print("  tier / family        %s / %s"
          % (entry.get("tier"), entry.get("family")))
    print("  prompt version       %s" % entry.get("prompt_version"))
    print("  trials / 试次        %d   (%d ordinary x1 + %d negative x3)"
          % (shape["trials"], shape["ordinary"], shape["negative"]))
    print("                       ^ derived from the fixtures, never typed")
    print()
    print("  ESTIMATE / 预估费用")
    print("    basis            %s" % est["basis"])
    print("    per trial        %.0f in / %.0f out tokens (x%g output safety)"
          % (est["tokens_in_per_trial"], est["tokens_out_per_trial"],
             est["output_factor"]))
    print("    battery total    %s in / %s out tokens"
          % ("{:,.0f}".format(est["total_in"]),
             "{:,.0f}".format(est["total_out"])))
    print("    price            in $%.4f/M  out $%.4f/M" % (est["price_in"],
                                                            est["price_out"]))
    print("    price source     %s" % est["price_source"])
    print("    ESTIMATED SPEND  US$%.4f" % est["usd"])
    print()
    print("  BUDGET / 预算")
    print("    per-member ceiling   US$%.2f   [brief §7]" % PER_MEMBER_CEILING_USD)
    print("    headroom / 余额      US$%.4f" % (PER_MEMBER_CEILING_USD - est["usd"]))
    print("    hard spend cap       US$%.2f   halts on MEASURED cost mid-run"
          % cap)
    print("    course key           US$%.2f total, no top-ups, A1 already"
          % COURSE_KEY_USD)
    print("                         spent some and the End-of-Course")
    print("                         Project still has to come out of it")
    print()
    say("The key is asked for on the next screen, hidden as you type.",
        "下一步会要求输入 Key，输入过程不显示，也不会写入任何文件。", "  ")
    say("It is never written to a file, never put in the environment,",
        "它只存在于内存中，结果文件里绝不会出现。", "  ")
    say("and never appears in a results file.", "", "  ")
    print()
    rule()


def confirm_bilingual(entry):
    say("Type the model id EXACTLY to proceed. Anything else aborts.",
        "请完整输入模型 id 以继续；输入其他内容即取消。", "  ")
    print("    %s" % entry["model"])
    got = input("  > ").strip()
    if got != entry["model"]:
        print()
        say("Aborted. Nothing was run and nothing was spent.",
            "已取消。未执行任何操作，也未产生任何费用。")
        print()
        return False
    return True


# =====================================================================
# THE PER-MEMBER COPY
# =====================================================================
def mirror_result(entry, dry_run):
    """Copy the canonical result into results/live/<member>/.

    run_battery writes results/live/battery__*.json and
    aggregate_battery.py globs exactly that, so the canonical file is
    the one the D5(b) table is built from and it must stay put. This is
    a SECOND copy under the member's own folder, in the naming the team
    agreed. Deleting the canonical one to tidy up would empty the table.
    """
    src_dir = os.path.join(ROOT, "results", "live",
                           "dryrun" if dry_run else "")
    files = sorted(glob.glob(os.path.join(src_dir, "battery__*.json")),
                   key=os.path.getmtime)
    if not files:
        return None
    latest = files[-1]
    with open(latest, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("member") != entry["member"]:
        return None                      # somebody else's file; leave it

    slug = str(doc.get("model", "model")).replace("/", "_").replace(":", "_")
    name = "problemA__live_%s_%s_%s.json" % (entry["member"], slug,
                                             doc.get("date", "undated"))
    out_dir = (os.path.join(ROOT, "results", "live", "dryrun",
                            entry["member"]) if dry_run
               else os.path.join(ROOT, "results", "live", entry["member"]))
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, name)
    shutil.copy2(latest, dest)
    return os.path.relpath(dest, ROOT), os.path.relpath(latest, ROOT)


# =====================================================================
# MAIN
# =====================================================================
def main(argv=None):
    global LANG
    ap = argparse.ArgumentParser(
        prog="run_live_battery.py",
        description="Bilingual front door to the D5(b) live battery. "
                    "D5(b) 实盘评测的双语启动器。")
    ap.add_argument("--name", help='your name, e.g. --name "Zhao Yujia" '
                                   'or --name yujia')
    ap.add_argument("--lang", choices=["en", "zh", "both"], default="both")
    ap.add_argument("--dry-run", action="store_true",
                    help="rehearse on the scripted backend: no network, "
                         "no key, no cost")
    ap.add_argument("--output-factor", type=float, default=3.0,
                    help="safety multiplier on the scripted output-token "
                         "floor (default 3)")
    ap.add_argument("--max-spend", type=float,
                    help="hard measured-cost cap, US$. Never raised above "
                         "the US$3 per-member ceiling.")
    ap.add_argument("--yes", action="store_true",
                    help="skip the typed confirmation (for --dry-run only)")
    ap.add_argument("--roster", default=prov.ROSTER_PATH)
    args, passthrough = ap.parse_known_args(argv)
    LANG = args.lang

    roster = prov.load_roster(args.roster)
    entry = resolve_member(roster, args.name) if args.name else None
    if entry is None:
        if args.name:
            raise SystemExit(
                "\n  Not on the roster: %r.\n"
                "  Known: %s\n"
                "  花名册中没有 %r。\n"
                % (args.name,
                   ", ".join(m["member"] for m in roster.get("members", [])),
                   args.name))
        entry = ask_for_name(roster)

    # ---- the roster row has to be real before we price anything ------
    model = str(entry.get("model", ""))
    if model.startswith("<") or not model:
        print()
        say("YOUR ROSTER ROW IS STILL A PLACEHOLDER: %s" % model,
            "你的花名册条目还是占位符：%s" % model)
        say("Nobody can run until evals/battery_roster.json carries a real",
            "在 evals/battery_roster.json 填入真实模型 id、当日核对的价格")
        say("model id, the price you checked on OpenRouter TODAY, and the",
            "以及核对日期之前，任何人都不能运行。")
        say("date you checked it. The brief requires the date.", "")
        print()
        return 2

    shape = prov.plan_shape(roster.get("problem"))
    est = estimate(entry, shape["trials"], args.output_factor)

    # ---- THE CEILING, ENFORCED -------------------------------------
    if not args.dry_run and est["usd"] > PER_MEMBER_CEILING_USD:
        print()
        rule()
        say("REFUSING TO START. The estimate breaks the per-member ceiling.",
            "拒绝启动：预估费用超过每人上限。")
        rule()
        print("    estimated   US$%.4f" % est["usd"])
        print("    ceiling     US$%.2f" % PER_MEMBER_CEILING_USD)
        print()
        say("The brief's remedy is explicit: cut trials, cut cases, or move",
            "简报给出的补救办法很明确：减少试次、减少用例，或把模型降一档，")
        say("this model down a tier - and say in the report that you did,",
            "并在报告中说明你这样做了，以及为什么。")
        say("and why. A %s-tier model at this token volume cannot fit."
            % entry.get("tier"), "")
        print()
        return 3

    cap = min(args.max_spend or entry.get("max_spend_usd") or 1.0,
              PER_MEMBER_CEILING_USD)

    banner(entry, shape, est, cap, args.dry_run)

    if not (args.yes and args.dry_run):
        if not confirm_bilingual(entry):
            return 1

    # ---- hand over to the real runner -------------------------------
    print()
    say("Handing over to evals/run_battery.py — provenance, drift checks,",
        "移交给 evals/run_battery.py —— 由它负责溯源、漂移检查、")
    say("checkpointing, key handling and the measured spend cap.",
        "断点续跑、Key 处理与实测费用上限。")
    print()

    inner = ["--member", entry["member"], "--max-spend", "%.4f" % cap,
             "--roster", args.roster]
    if args.dry_run:
        inner.append("--dry-run")
    inner += passthrough

    rc = battery.main(inner)

    if rc == 0:
        copied = mirror_result(entry, args.dry_run)
        if copied:
            dest, canonical = copied
            print()
            say("Your copy      %s" % dest, "你的副本      %s" % dest)
            say("Canonical      %s" % canonical,
                "汇总用文件    %s" % canonical)
            say("KEEP BOTH. aggregate_battery.py reads the canonical one;",
                "两个都要保留：aggregate_battery.py 只读汇总用文件；",)
            say("deleting it empties the D5(b) table.",
                "删掉它，D5(b) 结果表就是空的。")
            print()
            say("Commit both, then: python3 evals/aggregate_battery.py",
                "提交后运行：python3 evals/aggregate_battery.py")
            print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
