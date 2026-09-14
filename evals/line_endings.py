#!/usr/bin/env python3
"""
PE6201 · A2 — A WINDOWS CHECKOUT RUNS THE SAME EXPERIMENT  (D5b)
====================================================================
battery_provenance.fingerprint() hashes the answer key, the fixtures and
the pinned sources as raw bytes. Git for Windows usually checks text files
out with CRLF line endings, so a member who ran the identical commit there
records different hashes for identical content.

That happened on 2026-09-14. xia_yanran's and shen_bowen's batteries
record hashes that match no file in the tree, yet match every pinned
source, the answer key and the fixtures exactly once those files are
converted to CRLF. Their prompt, plan and invariant hashes, which are
computed from parsed content, already matched.

variants() hashes today's tree in both forms, so a comparison can accept a
recorded value that is either one. A change to any byte other than a line
ending matches neither.
====================================================================
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config                                        # noqa: E402
from evals import battery_provenance as prov         # noqa: E402

# The fingerprint fields hashed from raw bytes, and so the only ones a line
# ending can move.
BYTE_HASHED = ("answer_key_sha256", "fixtures_sha256", "sources_sha256")
FORMS = ("lf", "crlf")


def sha256_bytes(data, eol="lf"):
    """sha256 of `data` with every line ending rewritten to one form."""
    data = data.replace(b"\r\n", b"\n")
    if eol == "crlf":
        data = data.replace(b"\n", b"\r\n")
    return hashlib.sha256(data).hexdigest()


def form_of_bytes(data, sha):
    """'lf' or 'crlf' if `data` in that form hashes to `sha`, else None."""
    return next((eol for eol in FORMS if sha256_bytes(data, eol) == sha), None)


def _sha(path, eol):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read(), eol)


def tree_hashes(problem=None, eol="lf"):
    """The byte-hashed fingerprint fields of today's tree, with every file's
    line endings in one form. Mirrors battery_provenance.fingerprint()."""
    problem = problem or config.PROBLEM
    data = config.data_root()
    fixtures = os.path.join(data, "data_%s" % problem)
    return {
        "answer_key_sha256": _sha(os.path.join(data, "expected_outcomes_%s.json" % problem), eol),
        "fixtures_sha256": prov.sha256_json(
            {f: _sha(os.path.join(fixtures, f), eol)
             for f in sorted(os.listdir(fixtures)) if f.endswith(".json")}),
        "sources_sha256": {p: _sha(os.path.join(prov.ROOT, p), eol)
                           for p in prov.PINNED_SOURCES},
    }


def variants(problem=None):
    return {eol: tree_hashes(problem, eol) for eol in FORMS}


def form_of(field, value, forms):
    """'lf' or 'crlf' if a recorded scalar field is today's content in that
    form, else None."""
    for eol in FORMS:
        if value == forms[eol][field]:
            return eol
    return None


def same_content(fp, forms):
    """Does a recorded fingerprint describe today's files, line endings aside?

    Returns (ok, eols). ok is True only if the answer key, the fixtures and
    every pinned source match today's content in LF or CRLF form, and the
    recorded sources name exactly today's pinned files. eols is the set of
    forms that matched, so a caller can say which kind of checkout ran.
    """
    eols = set()
    for field in ("answer_key_sha256", "fixtures_sha256"):
        eol = form_of(field, fp.get(field), forms)
        if eol is None:
            return False, eols
        eols.add(eol)
    recorded = fp.get("sources_sha256") or {}
    if set(recorded) != set(prov.PINNED_SOURCES):
        return False, eols
    for path, value in recorded.items():
        eol = next((e for e in FORMS if value == forms[e]["sources_sha256"][path]), None)
        if eol is None:
            return False, eols
        eols.add(eol)
    return True, eols
