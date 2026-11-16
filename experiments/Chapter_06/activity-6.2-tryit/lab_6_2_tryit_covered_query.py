"""Lab 6.2 - Try It Yourself
Covered queries: a query is "covered" when every field it filters on AND
returns is present in one index, so MongoDB answers from the index alone
and never fetches the full document. This script builds a covered query and
uses explain() to verify that the FETCH stage is eliminated, next to two
queries that are NOT covered."""

import sys, os, random
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

FILTER = {"city": "Mumbai", "age": {"$gte": 30}}

VARIANTS = [
    ("A. Not covered - full documents returned",
     {"filter": FILTER}),
    ("B. Not covered - projection includes _id (forgot _id: 0)",
     {"filter": FILTER, "projection": {"city": 1, "age": 1}}),
    ("C. COVERED - only indexed fields, _id excluded",
     {"filter": FILTER, "projection": {"_id": 0, "city": 1, "age": 1}}),
]


def make_docs(count):
    return [{
        "user_id": i,
        "name": f"User {i}",
        "email": f"user{i}@example.com",
        "city": random.choice(CITIES),
        "age": random.randint(18, 65),
        "score": round(random.uniform(0, 100), 2),
    } for i in range(1, count + 1)]


def main():
    path = start_output_capture(__file__)
    random.seed(11)
    banner("Lab 6.2 (Try It Yourself): Covered Queries and the FETCH Stage")
    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "covered_query_demo")

    col.insert_many(make_docs(20000))
    print(f"[OK] Inserted {col.count_documents({})} documents.")
    col.create_index([("city", 1), ("age", 1)], name="idx_city_age")
    print("[OK] Created compound index idx_city_age on (city, age)\n")

    print("Query filter : {city: 'Mumbai', age: {$gte: 30}}")
    print("Index fields : city, age\n")

    # --- explain() every variant ---
    results = []
    print("=== explain() for each variant ===")
    for label, q in VARIANTS:
        r = explain_query(col, q)
        fetch_present = "FETCH" in r["stages"]
        covered = (not fetch_present) and r["docs_examined"] == 0
        print(f"  {label}")
        print(f"    plan            : {r['plan']}")
        print(f"    index used      : {r['index']}")
        print(f"    docs examined   : {r['docs_examined']}")
        print(f"    keys examined   : {r['keys_examined']}")
        print(f"    docs returned   : {r['n_returned']}")
        print(f"    FETCH stage     : {'PRESENT' if fetch_present else 'ELIMINATED'}")
        print(f"    covered query   : {'YES' if covered else 'NO'}\n")
        results.append({"variant": label, "projection": str(q.get("projection")),
                        "plan": r["plan"], "index": r["index"], "docs_examined": r["docs_examined"],
                        "keys_examined": r["keys_examined"], "n_returned": r["n_returned"],
                        "fetch_stage_present": fetch_present, "covered": covered})

    # --- timing: not covered vs covered ---
    print("=== Timing: not covered (A) vs covered (C), 300 runs each ===")
    t_a = benchmark(col, VARIANTS[0][1], 300)
    t_c = benchmark(col, VARIANTS[2][1], 300)
    print(f"  A. not covered : {t_a:.3f} ms/query")
    print(f"  C. covered     : {t_c:.3f} ms/query")
    print(f"  Covered query speedup: {t_a / t_c:.1f}x\n")

    # --- summary table ---
    table = Table(title="Covered query verification", show_lines=True, box=box.ASCII)
    table.add_column("Variant", width=52)
    table.add_column("Docs examined", justify="right")
    table.add_column("FETCH", width=12)
    table.add_column("Covered", width=8)
    for r in results:
        table.add_row(r["variant"], str(r["docs_examined"]),
                      "PRESENT" if r["fetch_stage_present"] else "ELIMINATED",
                      "YES" if r["covered"] else "NO")
    console.print(table)

    # --- Store results + export JSON ---
    res_col = reset_collection("nosql_labs", "covered_query_results")
    res_col.insert_many(results)
    res_col.insert_one({"variant": "timing", "not_covered_ms": round(t_a, 3),
                        "covered_ms": round(t_c, 3), "speedup_x": round(t_a / t_c, 2)})
    print(f"\n[OK] Stored {len(results) + 1} records in nosql_labs.covered_query_results")
    export_json(res_col, __file__, "covered_query_results.json")
    export_json(col, __file__, "covered_query_demo.json")
    print(f"[OK] Terminal output saved to {os.path.basename(path)}")

    banner("Lab 6.2 Try It Yourself Complete")


if __name__ == "__main__":
    main()
