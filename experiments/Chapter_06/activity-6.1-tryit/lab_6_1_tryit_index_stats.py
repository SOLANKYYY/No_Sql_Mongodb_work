"""Lab 6.1 - Try It Yourself
Use the $indexStats aggregation stage to measure real index usage.
The five workload queries from Lab 6.1 are run a different number of times
(a realistic, uneven workload), then $indexStats reports how often each
index was actually used so the most frequently used index can be identified."""

import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich import box
from rich.console import Console
from rich.table import Table
from config.connection import get_db, reset_collection, banner
from config.lab_utils import start_output_capture, export_json, make_cursor

console = Console(width=130)

CATEGORIES = ["Electronics", "Books", "Clothing", "Home", "Sports", "Toys", "Beauty", "Grocery"]
ADJECTIVES = ["Premium", "Compact", "Wireless", "Ergonomic", "Portable", "Smart", "Classic", "Pro"]
NOUNS = ["Keyboard", "Mouse", "Headphones", "Monitor", "Backpack", "Lamp", "Speaker", "Charger", "Notebook", "Bottle"]
TAGS = ["gaming", "office", "travel", "outdoor", "kids", "premium", "budget", "eco", "wireless", "gift",
        "sale", "new", "bestseller", "compact", "durable", "smart", "fitness", "home", "school", "luxury"]

# The same five queries as Lab 6.1, each with how many times the app runs it
WORKLOAD = [
    ("Q1", "Category + sort by price", 30,
     {"filter": {"category": "Electronics"}, "sort": [("price", 1)], "limit": 20}),
    ("Q2", "Price range 100 - 150", 10,
     {"filter": {"price": {"$gte": 100, "$lte": 150}}, "limit": 100}),
    ("Q3", "Tag lookup 'gaming'", 20,
     {"filter": {"tags": "gaming"}, "limit": 100}),
    ("Q4", "Text search 'wireless keyboard'", 5,
     {"filter": {"$text": {"$search": "\"wireless keyboard\""}}, "limit": 100}),
    ("Q5", "Category + rating, sort by price desc", 40,
     {"filter": {"category": "Books", "rating": {"$gte": 4.5}}, "sort": [("price", -1)], "limit": 20}),
]


def generate_products(count=50000):
    random.seed(42)
    docs = []
    for i in range(count):
        docs.append({
            "name": f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.randint(100, 9999)}",
            "category": random.choice(CATEGORIES),
            "price": round(random.uniform(5, 1000), 2),
            "rating": round(random.uniform(1, 5), 1),
            "stock": random.randint(0, 500),
            "tags": random.sample(TAGS, random.randint(2, 3)),
        })
    return docs


def main():
    path = start_output_capture(__file__)
    banner("Lab 6.1 (Try It Yourself): Measure Index Usage with $indexStats")
    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "products_tryit")

    print("Generating 50,000 products (may take a few seconds)...")
    col.insert_many(generate_products(50000))
    print(f"[OK] Inserted {col.count_documents({})} products.\n")

    # Same indexes as Lab 6.1
    col.create_index([("category", 1), ("price", 1), ("rating", 1)], name="idx_category_price_rating")
    col.create_index([("price", 1)], name="idx_price")
    col.create_index([("tags", 1)], name="idx_tags")
    col.create_index([("name", "text")], name="idx_name_text")
    print("[OK] Created 4 indexes (same design as Lab 6.1).\n")

    # --- Run the workload ---
    print("=== Running workload ===")
    for qid, label, repeats, q in WORKLOAD:
        for _ in range(repeats):
            list(make_cursor(col, q))
        print(f"  {qid} - {label:40} executed {repeats:3} times")

    # --- $indexStats ---
    print("\n=== $indexStats results ===")
    stats = list(col.aggregate([{"$indexStats": {}}]))
    stats.sort(key=lambda s: s["accesses"]["ops"], reverse=True)
    total_ops = sum(s["accesses"]["ops"] for s in stats) or 1

    table = Table(title="Index usage after workload", show_lines=True, box=box.ASCII)
    table.add_column("Index name", width=28)
    table.add_column("Key pattern", width=40)
    table.add_column("Ops", justify="right")
    table.add_column("Share of all ops", justify="right")
    rows = []
    for s in stats:
        ops = s["accesses"]["ops"]
        share = round(ops / total_ops * 100, 1)
        table.add_row(s["name"], str(dict(s["key"])), str(ops), f"{share}%")
        rows.append({
            "index_name": s["name"], "key_pattern": str(dict(s["key"])),
            "ops": ops, "share_pct": share, "tracking_since": s["accesses"]["since"],
        })
    console.print(table)

    most = stats[0]
    unused = [s["name"] for s in stats if s["accesses"]["ops"] == 0]
    print(f"\nMost frequently used index : {most['name']} "
          f"({most['accesses']['ops']} ops, {rows[0]['share_pct']}% of all index operations)")
    if unused:
        print(f"Indexes never used         : {', '.join(unused)}")
        print("  (an unused index only costs write throughput and storage - candidate to drop)")
    else:
        print("Every index was used at least once.")

    # --- Store results + export JSON ---
    res_col = reset_collection("nosql_labs", "index_stats_results")
    res_col.insert_many(rows)
    print(f"\n[OK] Stored {len(rows)} index usage records in nosql_labs.index_stats_results")
    export_json(res_col, __file__, "index_stats_results.json")
    export_json(col, __file__, "products_tryit_sample.json", limit=1000)
    print(f"[OK] Terminal output saved to {os.path.basename(path)}")

    banner("Lab 6.1 Try It Yourself Complete")


if __name__ == "__main__":
    main()
