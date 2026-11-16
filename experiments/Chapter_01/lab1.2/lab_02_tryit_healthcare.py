"""Lab 1.2 - Try It Yourself
Choose a different application domain (Healthcare) and repeat the
data-domain-to-NoSQL-family mapping exercise."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.connection import get_db, reset_collection, banner
from rich.table import Table
from rich.console import Console

console = Console()


def main():
    banner("Lab 1.2 (Try It Yourself): Map a Healthcare Application to NoSQL Families")

    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "app_domain_mapping_tryit")

    healthcare_domains = [
        {
            "app": "Healthcare Platform",
            "domain": "patient_records",
            "description": "Patient demographics, medical history, allergies, medications - "
                            "fields vary widely per patient",
            "read_write_pattern": "Read-heavy, occasional structured updates, needs flexible schema",
            "recommended_family": "Document",
            "recommended_db": "MongoDB",
            "rationale": "Patient records have a semi-structured, evolving schema (not every "
                         "patient has the same fields), so a document model avoids constant "
                         "schema migrations while still allowing indexed queries."
        },
        {
            "app": "Healthcare Platform",
            "domain": "vital_signs_stream",
            "description": "Continuous heart-rate, SpO2, and blood-pressure readings from "
                            "bedside/wearable monitors",
            "read_write_pattern": "Extremely write-heavy, time-ordered, queried by time range",
            "recommended_family": "Wide-Column",
            "recommended_db": "Apache Cassandra",
            "rationale": "Vital-sign streams are high-frequency, append-only, and queried by "
                         "patient + time range, which matches Cassandra's partitioned, "
                         "time-ordered wide-row model."
        },
        {
            "app": "Healthcare Platform",
            "domain": "provider_referral_network",
            "description": "Relationships between doctors, specialists, hospitals, and "
                            "patient referrals",
            "read_write_pattern": "Multi-hop traversal queries, e.g. 'find a specialist "
                                   "reachable through my GP's referral network'",
            "recommended_family": "Graph",
            "recommended_db": "Neo4j",
            "rationale": "Referral and provider networks are inherently relationship-centric, "
                         "so a graph database gives efficient traversal for referral chains, "
                         "fraud detection, and network analysis."
        },
        {
            "app": "Healthcare Platform",
            "domain": "medical_imaging",
            "description": "X-ray, MRI, and CT scan image/DICOM files linked to a patient record",
            "read_write_pattern": "Write-once, read-many, large binary objects delivered via CDN/PACS",
            "recommended_family": "Object/Key-Value",
            "recommended_db": "Amazon S3",
            "rationale": "Large binary imaging files are best stored as objects keyed by "
                         "patient/study ID rather than inside a database record, with "
                         "lightweight metadata pointers kept in MongoDB."
        },
    ]

    col.insert_many(healthcare_domains)
    print(f"[OK] Inserted {len(healthcare_domains)} healthcare domain mappings.\n")

    table = Table(title="Healthcare Platform - Data Domain Mapping (Try It Yourself)", show_lines=True)
    table.add_column("Domain", style="cyan", width=22)
    table.add_column("NoSQL Family", style="magenta", width=16)
    table.add_column("Recommended DB", style="green", width=18)
    table.add_column("Key Rationale", width=50)

    for d in col.find():
        table.add_row(d["domain"], d["recommended_family"], d["recommended_db"], d["rationale"])

    console.print(table)

    print("\n--- Family Distribution ---")
    pipeline = [
        {"$group": {"_id": "$recommended_family", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    for g in col.aggregate(pipeline):
        print(f"  {g['_id']:20} : {g['count']} domain(s)")

    banner("Lab 1.2 Try It Yourself Complete")


if __name__ == "__main__":
    main()
