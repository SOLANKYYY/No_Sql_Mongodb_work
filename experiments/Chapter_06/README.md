# Experiment 06 · Index design and query performance

Use execution plans and index usage counters to compare compound indexes, covered reads and the write cost of secondary indexes.

## Findings and evidence

Finding the 20 cheapest electronics examined 50,000 documents before indexing and 20 afterward. In a separate covered query, MongoDB returned 617 results while examining zero collection documents.

- [Before-and-after plans](activity-6.1/index_design_results.json)
- [Covered-query measurements](activity-6.2-tryit/covered_query_results.json)
- [Setup and lab commands](README.txt)

## Activities

- [6.1 Index design](activity-6.1/README.md)
- [6.1 extension · Index usage](activity-6.1-tryit/README.md)
- [6.2 Read and write trade-offs](activity-6.2/README.md)
- [6.2 extension · Covered queries](activity-6.2-tryit/README.md)

[All 18 experiments](../README.md)
