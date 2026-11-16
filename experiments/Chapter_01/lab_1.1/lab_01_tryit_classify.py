"""Lab 1.1 - Try It Yourself
Research and classify ScyllaDB, InfluxDB, and ArangoDB into NoSQL families,
and note whether each one fits neatly into a single family or spans multiple."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.connection import get_db, reset_collection, banner
from rich.table import Table
from rich.console import Console

console = Console()


def main():
    banner("Lab 1.1 (Try It Yourself): Classify ScyllaDB, InfluxDB, ArangoDB")

    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "database_products_tryit")

    products = [
        {
            "name": "ScyllaDB",
            "family": "Wide-Column",
            "data_model": "Column-Family (Cassandra-compatible)",
            "vendor": "ScyllaDB Inc.",
            "use_case": "Low-latency, high-throughput workloads (real-time analytics, IoT, ad-tech)",
            "spans_multiple_families": False,
            "reasoning": "ScyllaDB is a drop-in replacement for Apache Cassandra, "
                         "re-implemented in C++ for lower latency and higher throughput. "
                         "It keeps the same wide-column, partition/row data model and "
                         "wire protocol, so it fits neatly into a single family: Wide-Column."
        },
        {
            "name": "InfluxDB",
            "family": "Wide-Column / Time-Series",
            "data_model": "Time-series (measurement, tags, fields, timestamp)",
            "vendor": "InfluxData",
            "use_case": "Metrics, monitoring, sensor data, DevOps observability dashboards",
            "spans_multiple_families": True,
            "reasoning": "InfluxDB is purpose-built for time-series data with a "
                         "SQL-like query language (InfluxQL/Flux). It behaves like a "
                         "specialized Wide-Column store optimized purely for time-ordered "
                         "writes and range scans, so it is best treated as its own "
                         "Time-Series family rather than a generic Wide-Column store."
        },
        {
            "name": "ArangoDB",
            "family": "Multi-Model (Document + Graph + Key-Value)",
            "data_model": "JSON Document, Property Graph, Key-Value (single engine)",
            "vendor": "ArangoDB Inc.",
            "use_case": "Applications needing documents, graph traversals, and key-value "
                        "access without running three separate databases",
            "spans_multiple_families": True,
            "reasoning": "ArangoDB explicitly markets itself as a multi-model database: "
                         "the same storage engine and query language (AQL) can store JSON "
                         "documents, traverse graphs, and do simple key-value lookups. It "
                         "deliberately spans three NoSQL families instead of fitting into one."
        },
    ]

    col.insert_many(products)
    print(f"[OK] Inserted {len(products)} additional database products.\n")

    table = Table(title="Try It Yourself - Additional NoSQL Product Classification", show_lines=True)
    table.add_column("Product", style="cyan", width=12)
    table.add_column("Family", style="magenta", width=32)
    table.add_column("Spans Multiple?", width=16)
    table.add_column("Use Case", width=45)

    for p in col.find():
        table.add_row(p["name"], p["family"], "Yes" if p["spans_multiple_families"] else "No", p["use_case"])

    console.print(table)

    print("\n--- Reasoning ---")
    for p in col.find():
        print(f"\n{p['name']}:")
        print(f"  {p['reasoning']}")

    banner("Lab 1.1 Try It Yourself Complete")


if __name__ == "__main__":
    main()
