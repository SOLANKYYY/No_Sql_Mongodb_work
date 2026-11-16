"""Lab 6.2 - Compare Index Strategies
Measure how indexes change write throughput and read performance:
 1. Insert 10,000 documents with no indexes (except _id) and time it.
 2. Create 5 indexes, insert another 10,000 documents, time it, and
    calculate the percentage slowdown.
 3. Drop all but the most critical index and re-run five representative
    queries to compare read performance.
 4. Print a short analysis of the query-performance vs write-throughput trade-off."""

import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich import box
from rich.console import Console
from rich.table import Table
from config.connection import get_db, reset_collection, banner
from config.lab_utils import start_output_capture, export_json, benchmark, explain_query

console = Console(width=130)

CITIES = ["Bengaluru", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad", "Jaipur",
          "Surat", "Lucknow", "Kanpur", "Nagpur", "Indore", "Bhopal", "Patna", "Vadodara", "Ludhiana",
          "Agra", "Nashik", "Kochi", "Mysuru", "Goa", "Noida", "Gurugram"]

# Five representative queries
QUERIES = [
    ("Q1 user_id lookup", {"filter": {"user_id": 15000}}),
    ("Q2 email lookup", {"filter": {"email": "user7500@example.com"}}),
    ("Q3 city equality", {"filter": {"city": "Bengaluru"}}),
    ("Q4 age range 30-31", {"filter": {"age": {"$gte": 30, "$lte": 31}}}),
    ("Q5 score >= 99.5", {"filter": {"score": {"$gte": 99.5}}}),
]
ITERATIONS = 20
CRITICAL_INDEX = "idx_user_id"


def make_docs(start, count):
    return [{
        "user_id": i,
        "email": f"user{i}@example.com",
        "name": f"User {i}",
        "city": random.choice(CITIES),
        "age": random.randint(18, 65),
        "score": round(random.uniform(0, 100), 2),
    } for i in range(start, start + count)]


def timed_insert(col, docs, label):
    start = time.perf_counter()
    col.insert_many(docs)
    elapsed = time.perf_counter() - start
    print(f"  {label}: {len(docs)} inserts in {elapsed:.3f}s = {len(docs) / elapsed:,.0f} docs/sec")
    return elapsed


def run_read_benchmark(col, label):
    print(f"\n=== Read benchmark: {label} ({ITERATIONS} runs per query) ===")
    out = {}
    for name, q in QUERIES:
        ms = benchmark(col, q, ITERATIONS)
        plan = explain_query(col, q)
        out[name] = {"ms_per_query": round(ms, 3), "plan": plan["plan"], "docs_examined": plan["docs_examined"]}
        print(f"  {name:22} {ms:8.3f} ms/query   plan={plan['plan']}   docs_examined={plan['docs_examined']}")
    return out


def main():
    path = start_output_capture(__file__)
    random.seed(7)
    banner("Lab 6.2: Compare Index Strategies")
    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "write_perf_test")

    # --- Step 1: insert 10,000 docs with no indexes except _id ---
    print("=== Step 1: Insert 10,000 documents with NO indexes (except _id) ===")
    t_no_idx = timed_insert(col, make_docs(1, 10000), "0 extra indexes")

    # --- Step 2: create 5 indexes, insert another 10,000 docs ---
    print("\n=== Step 2: Create 5 indexes, then insert another 10,000 documents ===")
    col.create_index([("user_id", 1)], name="idx_user_id")
    col.create_index([("email", 1)], name="idx_email")
    col.create_index([("city", 1)], name="idx_city")
    col.create_index([("age", 1)], name="idx_age")
    col.create_index([("score", 1)], name="idx_score")
    print("  Created: idx_user_id, idx_email, idx_city, idx_age, idx_score")
    t_5_idx = timed_insert(col, make_docs(10001, 10000), "5 extra indexes")
    slowdown_pct = (t_5_idx - t_no_idx) / t_no_idx * 100
    print(f"\n  Write slowdown with 5 indexes: {slowdown_pct:+.1f}%")

    # --- Step 3: read performance with all indexes, then with only the critical one ---
    with_all = run_read_benchmark(col, "all 5 indexes present")

    print(f"\n=== Step 3: Drop all indexes except {CRITICAL_INDEX} (the most critical) ===")
    for idx in list(col.list_indexes()):
        if idx["name"] not in ("_id_", CRITICAL_INDEX):
            col.drop_index(idx["name"])
            print(f"  dropped {idx['name']}")
    with_one = run_read_benchmark(col, f"only {CRITICAL_INDEX} kept")

    # --- comparison table ---
    print()
    table = Table(title="Read performance: 5 indexes vs 1 index", show_lines=True, box=box.ASCII)
    table.add_column("Query", width=22)
    table.add_column("5 idx (ms)", justify="right")
    table.add_column("1 idx (ms)", justify="right")
    table.add_column("Slower by", justify="right")
    table.add_column("Plan with 1 index", width=26)
    comparison = []
    for name, _ in QUERIES:
        a, b = with_all[name], with_one[name]
        factor = b["ms_per_query"] / a["ms_per_query"] if a["ms_per_query"] else 0
        table.add_row(name, f"{a['ms_per_query']:.3f}", f"{b['ms_per_query']:.3f}", f"{factor:.1f}x", b["plan"])
        comparison.append({"query": name, "ms_5_indexes": a["ms_per_query"], "ms_1_index": b["ms_per_query"],
                           "slower_by_factor": round(factor, 2), "plan_1_index": b["plan"],
                           "plan_5_indexes": a["plan"]})
    console.print(table)

    # --- Step 4: analysis (built from the measured numbers) ---
    collscan = [c["query"] for c in comparison if "COLLSCAN" in c["plan_1_index"]]
    slower = [c["query"] for c in comparison if c["slower_by_factor"] >= 1.5]
    analysis = (
        f"Inserting 10,000 documents took {t_no_idx:.3f}s with no indexes and {t_5_idx:.3f}s with 5 indexes "
        f"({slowdown_pct:+.1f}% write time; {10000 / t_no_idx:,.0f} vs {10000 / t_5_idx:,.0f} docs/sec), "
        f"because every insert must also update all 5 index B-trees. In return, indexed queries read only "
        f"matching entries instead of scanning the whole collection. After dropping to the single "
        f"{CRITICAL_INDEX} index, {len(collscan)} of 5 queries fell back to COLLSCAN "
        f"({', '.join(collscan) if collscan else 'none'}) and {len(slower)} of 5 became at least 1.5x slower "
        f"({', '.join(slower) if slower else 'none'}). Trade-off: every extra index buys read speed for "
        f"the queries it serves but costs write throughput and storage on every insert, so keep only the "
        f"indexes that serve frequent, selective queries. Read-heavy workloads justify more indexes; "
        f"write-heavy workloads (logs, IoT) should keep them minimal."
    )
    print("\n=== Step 4: Analysis - query performance vs write throughput ===")
    print("  " + analysis)

    # --- Store results + export JSON ---
    res_col = reset_collection("nosql_labs", "index_strategy_results")
    res_col.insert_one({
        "insert_10k_no_indexes_sec": round(t_no_idx, 4),
        "insert_10k_5_indexes_sec": round(t_5_idx, 4),
        "write_slowdown_pct": round(slowdown_pct, 2),
        "critical_index_kept": CRITICAL_INDEX,
        "read_comparison": comparison,
        "analysis": analysis,
    })
    print("\n[OK] Stored results in nosql_labs.index_strategy_results")
    export_json(res_col, __file__, "index_strategy_results.json")
    export_json(col, __file__, "write_perf_test.json")
    print(f"[OK] Terminal output saved to {os.path.basename(path)}")

    banner("Lab 6.2 Complete")


if __name__ == "__main__":
    main()
