# Activity_10.2

Inventory reservations, concurrent contention, order-failure rollback and throughput.

`lab_10_2_inventory.json` and `observed_output.txt` contain the original submitted measurements.
Full Python implementation is in `../Docker_Kit/transactions.py` and `../Docker_Kit/lab10.py`.

From this folder, run a fresh experiment with Docker Desktop running:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

The launcher uses the exact published image and shared Exercise 10 replica set.
New JSON goes to `../Docker_Kit/results`; these original activity evidence files stay unchanged.
Use the root `DEMONSTRATE.ps1` for a complete fresh run and report.
