"""Lab 6.1 - Index Design for a Query Workload
Create a 50,000-document products collection, run five representative
queries through explain() BEFORE any index exists, design indexes that cover
all five queries, then run explain() again and compare the results."""

import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo.errors import OperationFailure
from rich import box
from rich.console import Console
from rich.table import Table
from config.connection import get_db, reset_collection, banner
from config.lab_utils import start_output_capture, export_json, explain_query

console = Console(width=130)

CATEGORIES = ["Electronics", "Books", "Clothing", "Home", "Sports", "Toys", "Beauty", "Grocery"]
ADJECTIVES = ["Premium", "Compact", "Wireless", "Ergonomic", "Portable", "Smart", "Classic", "Pro"]
NOUNS = ["Keyboard", "Mouse", "Headphones", "Monitor", "Backpack", "Lamp", "Speaker", "Charger", "Notebook", "Bottle"]
TAGS = ["gaming", "office", "travel", "outdoor", "kids", "premium", "budget", "eco", "wireless", "gift",
        "sale", "new", "bestseller", "compact", "durable", "smart", "fitness", "home", "school", "luxury"]

# Five representative queries for the products collection
QUERIES = [
    {"id": "Q1", "label": "Category + sort by price (20 cheapest Electronics)",
     "filter": {"category": "Electronics"}, "sort": [("price", 1)], "limit": 20},
    {"id": "Q2", "label": "Price range 100 - 150",
     "filter": {"price": {"$gte": 100, "$lte": 150}}},
    {"id": "Q3", "label": "Tag lookup: tags = 'gaming'",
     "filter": {"tags": "gaming"}},
    {"id": "Q4", "label": "Text search on name: \"wireless keyboard\"",
     "filter": {"$text": {"$search": "\"wireless keyboard\""}},
     "baseline_filter": {"name": {"$regex": "wireless keyboard", "$options": "i"}}},
    {"id": "Q5", "label": "Category + rating >= 4.5, sorted by price desc",
     "filter": {"category": "Books", "rating": {"$gte": 4.5}}, "sort": [("price", -1)], "limit": 20},
]


def generate_products(count=50000):
    """Generate synthetic product documents with random data."""
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


def explain_before(col, q):
    """explain() a query with no index. $text cannot run without a text index."""
    try:
        return explain_query(col, q)
    except OperationFailure:
        # $text needs a text index: fall back to a regex query as the baseline
        print(f"  {q['id']}: $text query cannot run without a text index (server error).")
        print(f"  {q['id']}: using an equivalent regex query as the no-index baseline.")
        baseline = dict(q, filter=q["baseline_filter"])
        result = explain_query(col, baseline)
        result["note"] = "baseline uses regex because $text requires a text index"
        return result


def print_plan(tag, r):
    print(f"    {tag}: plan={r['plan']}")
    print(f"           index={r['index']}  docs_examined={r['docs_examined']}  "
          f"keys_examined={r['keys_examined']}  returned={r['n_returned']}  time={r['exec_ms']} ms")


def main():
    path = start_output_capture(__file__)
    banner("Lab 6.1: Index Design for a Query Workload")
    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "products")

    # --- Step 1: create 50,000 products ---
    print("Generating 50,000 products (may take a few seconds)...")
    col.insert_many(generate_products(50000))
    print(f"[OK] Inserted {col.count_documents({})} products.")
    print("Sample document:")
    sample = col.find_one({}, {"_id": 0})
    print(f"  {sample}\n")

    # --- Step 2/3: explain() before creating any index ---
    print("=== EXPLAIN: Before creating any index ===")
    before = {}
    for q in QUERIES:
        print(f"  {q['id']} - {q['label']}")
        before[q["id"]] = explain_before(col, q)
        print_plan("BEFORE", before[q["id"]])

    # --- Step 4: design indexes covering all five queries ---
    print("\n=== Creating Indexes ===")
    col.create_index([("category", 1), ("price", 1), ("rating", 1)], name="idx_category_price_rating")
    print("  idx_category_price_rating  (ESR: category=Equality, price=Sort, rating=Range) -> Q1, Q5")
    col.create_index([("price", 1)], name="idx_price")
    print("  idx_price                  (range scan on price)                              -> Q2")
    col.create_index([("tags", 1)], name="idx_tags")
    print("  idx_tags                   (multikey index on the tags array)                 -> Q3")
    col.create_index([("name", "text")], name="idx_name_text")
    print("  idx_name_text              (text index on name)                               -> Q4")
    print("[OK] Created 4 indexes covering all 5 queries.\n")

    # --- explain() after ---
    print("=== EXPLAIN: After creating indexes ===")
    after = {}
    for q in QUERIES:
        print(f"  {q['id']} - {q['label']}")
        after[q["id"]] = explain_query(col, q)
        print_plan("AFTER ", after[q["id"]])

    # --- Comparison summary ---
    print()
    table = Table(title="Before vs After: totalDocsExamined", show_lines=True, box=box.ASCII)
    table.add_column("Query", width=8)
    table.add_column("Before plan", width=24)
    table.add_column("Docs before", justify="right")
    table.add_column("After plan", width=32)
    table.add_column("Docs after", justify="right")
    table.add_column("Index used", width=26)
    results = []
    for q in QUERIES:
        b, a = before[q["id"]], after[q["id"]]
        table.add_row(q["id"], b["plan"], str(b["docs_examined"]), a["plan"],
                      str(a["docs_examined"]), str(a["index"]))
        reduction = None
        if b["docs_examined"]:
            reduction = round((1 - (a["docs_examined"] or 0) / b["docs_examined"]) * 100, 2)
        results.append({
            "query_id": q["id"], "label": q["label"],
            "filter": json.dumps(q["filter"]),
            "sort": str(q.get("sort")), "limit": q.get("limit", 0),
            "before": before[q["id"]], "after": after[q["id"]],
            "docs_examined_reduction_pct": reduction,
        })
    console.print(table)

    print("\n=== Index Summary ===")
    for idx in col.list_indexes():
        print(f"  {idx['name']:28} keys={dict(idx['key'])}")

    # --- Store results + export JSON ---
    res_col = reset_collection("nosql_labs", "index_design_results")
    res_col.insert_many(results)
    print(f"\n[OK] Stored {len(results)} before/after comparisons in nosql_labs.index_design_results")
    export_json(res_col, __file__, "index_design_results.json")
    export_json(col, __file__, "products.json")
    print(f"[OK] Terminal output saved to {os.path.basename(path)}")

    banner("Lab 6.1 Complete")


if __name__ == "__main__":
    main()
