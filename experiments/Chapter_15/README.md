# Experiment 15 · Multi-tenant task API and data migration

Enforce tenant and owner boundaries in a task API, apply a request limit and verify migration of tenant data.

## Findings and evidence

The API checks recorded 20 accepted requests and 10 rate-limited responses in a concurrent burst. The migration covered five tenants with 100 documents each and compared counts and checksums per tenant.

- [Task API implementation](Experiment_15_Submission/scripts/api.py)
- [Access and rate-limit checks](Experiment_15_Submission/results/lab15_1_api.json)
- [Migration verification](Experiment_15_Submission/results/lab15_2_migration.json)
- [Chapter report](Experiment_15_Submission/results/Exercise_15_Final_Report.pdf)
- [Docker setup and run guide](Experiment_15_Submission/README.md)

[All 18 experiments](../README.md)
