#!/usr/bin/env python3
"""check_labels_A.py — arithmetic and reference checks on the answer key.

Deliberately does NOT compute expected_decision. That judgement is yours and it
is what D4 marks. This checks the NUMBERS and REFERENCES inside each label
against the fixtures, which is where hand-written labels actually go wrong.

Run from the same folder as make_fixtures_A.py:   python3 check_labels_A.py
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data_A")
L = lambda n: json.load(open(os.path.join(D, n + ".json"), encoding="utf-8"))

claims    = {c["claim_id"]: c for c in L("claims")}
members   = {m["member_id"]: m for m in L("members")}
policies  = {p["policy_id"]: p for p in L("policies")}
hospitals = {h["hospital_id"]: h for h in L("hospitals")}
procs     = {p["code"]: p for p in L("procedures")}
preauths  = L("preauthorisations")
decided   = L("decided_claims")
reqdocs   = {r["procedure_code"]: r["document"] for r in L("required_documents")}
key = json.load(open(os.path.join(HERE, "expected_outcomes_A.json"), encoding="utf-8"))

bad, warn = [], []
lineset = lambda ls: sorted((l["code"], l["amount"]) for l in ls)

for lab in key:
    cid = lab["case_id"]
    c = claims.get(cid)
    if not c:
        bad.append(f"{cid}: labelled but no such claim"); continue
    mem = members.get(c["member_id"])
    if not mem:
        bad.append(f"{cid}: member {c['member_id']} does not resolve"); continue
    pol = policies.get(mem["policy_id"])
    dos = c["date_of_service"]
    remaining = pol["annual_limit"] - pol["used_to_date"]
    total = sum(l["amount"] for l in c["lines"])
    excl = {e["code"]: e["rule"] for e in pol["exclusions"]}
    approved = sum(l["amount"] for l in c["lines"] if l["code"] not in excl)
    refused  = total - approved
    text = " ".join(lab.get("must_record", []))
    dec = lab["expected_decision"]

    # --- structural ---------------------------------------------------------
    if dec not in ("approve_in_principle", "request_document", "escalate"):
        bad.append(f"{cid}: unknown decision {dec!r}")
    if dec == "escalate" and "trigger" not in lab:
        bad.append(f"{cid}: escalate with no trigger")
    if dec == "request_document" and "missing" not in lab:
        bad.append(f"{cid}: request_document with no missing item")
    if dec == "approve_in_principle" and ("trigger" in lab or "missing" in lab):
        bad.append(f"{cid}: approve carries a trigger or missing field")

    # --- arithmetic claimed in must_record ----------------------------------
    def num(pat):
        m = re.search(pat, text)
        return int(m.group(1)) if m else None
    for label, claimed, actual in (
        ("approved_total", num(r"approved_total (\d+)"), approved),
        ("refused_total",  num(r"refused_total (\d+)"),  refused),
        ("claim total",    num(r"claim total (\d+)"),    total)):
        if claimed is not None and dec == "approve_in_principle" and claimed != actual:
            bad.append(f"{cid}: {label} says {claimed}, fixtures give {actual}")
        elif claimed is not None and label == "claim total" and claimed != actual:
            bad.append(f"{cid}: claim total says {claimed}, fixtures give {total}")
    m = re.search(r"(\d+) remaining on (POL-\d+)", text)
    if m:
        n, pid = int(m.group(1)), m.group(2)
        if pid != pol["policy_id"]:
            bad.append(f"{cid}: names {pid}, member is on {pol['policy_id']}")
        elif n != remaining:
            bad.append(f"{cid}: remaining says {n}, fixtures give {remaining}")

    # --- every id named in the label must exist -----------------------------
    for pid in set(re.findall(r"PA-\d+", text)):
        if not any(p["preauth_id"] == pid for p in preauths):
            bad.append(f"{cid}: names {pid}, which does not exist")
    for pid in set(re.findall(r"POL-\d+", text)):
        if pid not in policies: bad.append(f"{cid}: names {pid}, which does not exist")
    for hid in set(re.findall(r"H-\d+", text)):
        if hid not in hospitals: bad.append(f"{cid}: names {hid}, which does not exist")
    for xid in set(re.findall(r"CLM-\d+", text)):
        if xid not in claims and not any(d["claim_id"] == xid for d in decided):
            bad.append(f"{cid}: names {xid}, which does not exist")
    for rule in set(re.findall(r"EX-\d+[^\",]*", text)):
        if rule.strip() and not any(rule.strip().startswith(v.split()[0]) for v in excl.values()):
            warn.append(f"{cid}: rule text {rule.strip()!r} not on {pol['policy_id']}")

    # --- deterministic facts, cross-checked against the label ---------------
    dup = [d for d in decided if d["member_id"] == c["member_id"]
           and d["hospital_id"] == c["hospital_id"]
           and d["date_of_service"] == dos
           and lineset(d["lines"]) == lineset(c["lines"])]
    if dup and lab.get("trigger") != "duplicate_claim":
        bad.append(f"{cid}: matches decided {dup[0]['claim_id']} on all four facts "
                   f"but is not labelled duplicate_claim")
    if lab.get("trigger") == "duplicate_claim" and not dup:
        bad.append(f"{cid}: labelled duplicate_claim but nothing in the history matches")

    missing_docs = [l["code"] for l in c["lines"]
                    if reqdocs.get(l["code"]) and reqdocs[l["code"]] not in c["documents"]]
    if missing_docs and dec == "approve_in_principle":
        bad.append(f"{cid}: labelled approve but lines {missing_docs} are missing a required document")

    for l in c["lines"]:
        p = procs.get(l["code"])
        if not p:
            bad.append(f"{cid}: line code {l['code']} is not in procedures"); continue
        if p["requires_preauth"]:
            ok = [a for a in preauths if a["member_id"] == c["member_id"]
                  and a["procedure_code"] == l["code"]
                  and a["valid_from"] <= dos <= a["valid_to"]]
            if not ok and dec == "approve_in_principle" and l["code"] not in excl:
                bad.append(f"{cid}: labelled approve but line {l['code']} needs a "
                           f"pre-authorisation valid on {dos} and none is")
    if total > remaining and lab.get("trigger") != "annual_limit_exceeded":
        warn.append(f"{cid}: total {total} exceeds remaining {remaining} "
                    f"but trigger is {lab.get('trigger')!r}")

for cid in claims:
    if not any(l["case_id"] == cid for l in key):
        bad.append(f"{cid}: claim with no label")

for w in warn: print("WARN ", w)
for b in bad:  print("FAIL ", b)
print(f"\n{len(key)} labels · {len(bad)} failures · {len(warn)} warnings")
sys.exit(1 if bad else 0)