# Experiment 04 · Product queries and bulk imports

Filter and paginate an Amazon product catalogue, search product titles and import inventory by ASIN using upserts.

## Findings and evidence

The saved title-search output covers 50,000 documents. The inventory export contains six records. The bulk importer checks that repeating the same import leaves the document count unchanged.

- [Search results](Activity_4.1_Try_It_Yourself/activity_4_1_try_it_yourself_search_results.json)
- [Import record](Activity_4.2_Try_It_Yourself/activity_4_2_try_it_yourself_catalog_import.json)
- [Chapter report](Chapter04_Activities_Report.docx)

## Activities

- [4.1 Product query API](Activity_4.1/README.md)
- [4.1 extension · Product title search](Activity_4.1_Try_It_Yourself/README.md)
- [4.2 Inventory upserts and bulk writes](Activity_4.2/README.md)
- [4.2 extension · Repeatable catalogue import](Activity_4.2_Try_It_Yourself/README.md)

To rerun the catalogue queries, first populate `nosql_labs.products`. The scripts refer to an external `load_amazon_products.py` loader. The activity folders include exported data for reviewing the exercise.

[All 18 experiments](../README.md)
