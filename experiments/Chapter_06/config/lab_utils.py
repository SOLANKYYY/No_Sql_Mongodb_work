"""Shared helpers for the Exercise 6 scripts.

- start_output_capture(): copies everything printed to the terminal into
  output.txt (UTF-8) next to the running script.
- export_json(): writes a collection to a JSON file next to the script
  (Compass-importable Extended JSON).
- make_cursor(), benchmark(): run / time a query described by a small dict.
- plan_summary(): reduces an explain() document to the few numbers we need.
"""

import atexit
import os
import sys
import time

from bson import json_util


# ---------------------------------------------------------------- output capture
class _Tee:
    """File-like object that writes to the terminal and to output.txt."""

    def __init__(self, terminal, log_file):
        self.terminal = terminal
        self.log_file = log_file
        self.encoding = "utf-8"

    def write(self, data):
        try:
            self.terminal.write(data)
        except UnicodeEncodeError:
            self.terminal.write(data.encode("ascii", "replace").decode("ascii"))
        self.log_file.write(data)
        return len(data)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def isatty(self):
        return False


def start_output_capture(script_file, filename="output.txt"):
    """Mirror stdout into <script folder>/output.txt."""
    path = os.path.join(os.path.dirname(os.path.abspath(script_file)), filename)
    log_file = open(path, "w", encoding="utf-8")
    original = sys.stdout
    sys.stdout = _Tee(original, log_file)

    def _close():
        try:
            sys.stdout.flush()
        except Exception:
            pass
        sys.stdout = original
        log_file.close()

    atexit.register(_close)
    return path


# ---------------------------------------------------------------- JSON export
def export_json(col, script_file, filename, limit=None):
    """Write a collection to <script folder>/<filename> as a JSON array."""
    path = os.path.join(os.path.dirname(os.path.abspath(script_file)), filename)
    cursor = col.find({})
    if limit:
        cursor = cursor.limit(limit)
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n")
        for doc in cursor:
            if count:
                f.write(",\n")
            f.write(json_util.dumps(doc))
            count += 1
        f.write("\n]\n")
    print(f"[OK] Exported {count} documents from '{col.name}' to {filename}")
    return path


# ---------------------------------------------------------------- query helpers
def make_cursor(col, q):
    """Build a cursor from a query dict: filter / projection / sort / limit."""
    return col.find(
        q["filter"],
        q.get("projection"),
        limit=q.get("limit", 0),
        sort=q.get("sort"),
    )


def benchmark(col, q, iterations):
    """Run the query `iterations` times, return average milliseconds per run."""
    start = time.perf_counter()
    for _ in range(iterations):
        list(make_cursor(col, q))
    return (time.perf_counter() - start) / iterations * 1000


# ---------------------------------------------------------------- explain helpers
def _walk(node, stages, indexes):
    if not isinstance(node, dict):
        return
    if "stage" in node:
        stages.append(node["stage"])
    if "indexName" in node:
        indexes.append(node["indexName"])
    for key in ("queryPlan", "inputStage", "outerStage", "innerStage"):
        if key in node:
            _walk(node[key], stages, indexes)
    for child in node.get("inputStages", []):
        _walk(child, stages, indexes)


def plan_summary(explain_doc):
    """Reduce an explain() result to plan shape + execution numbers."""
    winning = explain_doc.get("queryPlanner", {}).get("winningPlan", {})
    stages, indexes = [], []
    _walk(winning, stages, indexes)
    stats = explain_doc.get("executionStats", {})
    return {
        "plan": " -> ".join(stages) if stages else "UNKNOWN",
        "stages": stages,
        "index": indexes[0] if indexes else None,
        "docs_examined": stats.get("totalDocsExamined"),
        "keys_examined": stats.get("totalKeysExamined"),
        "n_returned": stats.get("nReturned"),
        "exec_ms": stats.get("executionTimeMillis"),
    }


def explain_query(col, q):
    """explain() a query dict and return its plan_summary()."""
    return plan_summary(make_cursor(col, q).explain())
