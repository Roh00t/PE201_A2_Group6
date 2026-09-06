"""
PE6201 · A2 — BATTERY CHECKPOINT  (D5b)
====================================================================
Sixty live calls on a US$10 key that has to last the rest of the course.
Something will interrupt one of them: a rate limit, a dropped wifi, a
closed laptop lid, a Ctrl-C. Without a checkpoint, an interruption at
trial 45 loses the money spent on all 45 and the member starts again.

FORMAT: APPEND-ONLY JSONL, flushed and fsync'd per line. Not a JSON
document. A document has to be rewritten whole on every trial, and a
crash during that rewrite destroys the record of everything already
paid for - the crash-safety feature failing in exactly the situation it
exists for.

AND THE READER TOLERATES A TRUNCATED LAST LINE. A process killed
mid-write leaves half a line. A reader that raises on it throws away the
44 good lines above it, which is the same data loss the checkpoint was
built to prevent, arriving by a different door.
====================================================================
"""
import json
import os
import socket
import time


class CheckpointConflict(Exception):
    """The checkpoint on disk belongs to a different experiment."""


class Locked(Exception):
    """Another process holds this checkpoint."""


class Checkpoint(object):

    def __init__(self, path, header):
        self.path = path
        self.header = header
        self._fh = None
        self._records = []
        self._warnings = []

    # ---- lifecycle ---------------------------------------------------
    @classmethod
    def open(cls, path, header):
        """New file -> write the header. Existing file -> read it and
        REFUSE if its fingerprint differs from ours.

        Refusing matters: silently resuming a battery started before an
        edit would produce one results file whose first 30 trials ran
        against one experiment and whose last 30 ran against another.
        Nothing about the output would look wrong.
        """
        cp = cls(path, header)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            cp._records, cp._warnings = _read_jsonl(path)
            existing = next((r for r in cp._records
                             if r.get("kind") == "header"), None)
            if existing and existing.get("fingerprint") != header.get("fingerprint"):
                raise CheckpointConflict(
                    "the checkpoint at %s was written for a DIFFERENT "
                    "experiment.\n  Its run_id is %s; yours is %s.\n"
                    "  Something changed between then and now - the answer "
                    "key, a descriptor, the grouping.\n  Start a fresh "
                    "battery rather than mixing two experiments in one file."
                    % (os.path.basename(path), existing.get("run_id"),
                       header.get("run_id")))
            cp._fh = open(path, "a", encoding="utf-8")
        else:
            cp._fh = open(path, "a", encoding="utf-8")
            cp.append(dict(header, kind="header"))
        return cp

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None

    # ---- writing -----------------------------------------------------
    def append(self, record):
        """One line, flushed AND fsync'd. The fsync is the point: without
        it the line sits in an OS buffer and a hard power loss takes it,
        which is precisely the scenario this file exists for."""
        record.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
        self._fh.write(json.dumps(record, default=str) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._records.append(record)

    # ---- reading -----------------------------------------------------
    def records(self, kind=None):
        return [r for r in self._records if kind is None or r.get("kind") == kind]

    def done(self):
        """(case_id, trial) pairs already completed AND graded."""
        return {(r["case_id"], r["trial"]) for r in self.records("trial")}

    def errored(self):
        """Trials that failed in transport. Re-runnable with --retry-errors;
        a network problem is not evidence about a model."""
        return {(r["case_id"], r["trial"]) for r in self.records("error")}

    def results(self):
        """The graded results, in the shape harness.run_set returns."""
        return [{k: r[k] for k in ("case_id", "trial", "passed", "fails",
                                   "record", "family") if k in r}
                for r in self.records("trial")]

    def spend_usd(self):
        return sum(float((r.get("record") or {}).get("cost_usd") or 0.0)
                   for r in self.records("trial"))

    @property
    def warnings(self):
        return list(self._warnings)

    # ---- the lock ----------------------------------------------------
    def lock(self, force=False):
        """Stop a member double-spending by resuming the same battery in
        two terminals. Both would append to this file, interleave
        mid-line, and pay twice for the same trials."""
        lock_path = self.path + ".lock"
        if os.path.exists(lock_path) and not force:
            try:
                held = open(lock_path, encoding="utf-8").read().strip()
            except OSError:
                held = "(unreadable)"
            raise Locked(
                "another process holds this battery:\n    %s\n"
                "  If that process is genuinely dead, re-run with "
                "--force-unlock (it is recorded in the checkpoint)."
                % held)
        with open(lock_path, "w", encoding="utf-8") as fh:
            fh.write("pid %d on %s at %s\n"
                     % (os.getpid(), socket.gethostname(),
                        time.strftime("%Y-%m-%dT%H:%M:%S")))

    def unlock(self):
        try:
            os.remove(self.path + ".lock")
        except OSError:
            pass


def _read_jsonl(path):
    """Every parseable line, plus a warning for each that is not.

    A truncated trailing line is the expected outcome of a kill -9 during
    a write. Dropping it with a warning keeps everything above it; raising
    would lose the whole file.
    """
    records, warnings = [], []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                warnings.append(
                    "line %d of %s is not valid JSON and was dropped - almost "
                    "certainly a write interrupted mid-line. The %d record(s) "
                    "above it are intact."
                    % (n, os.path.basename(path), len(records)))
    return records, warnings


def path_for(root, member, run_id):
    return os.path.join(root, "results", "live", "checkpoints",
                        "battery__%s__%s.jsonl" % (member, run_id))
