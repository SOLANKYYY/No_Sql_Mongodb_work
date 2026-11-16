# Durability_and_Journaling

Additional durability verification: committed documents survive an unclean restart. The filename 10_3 is retained from the original implementation; this is additional evidence, not an extra required assignment lab.

`lab_10_3_durability.json` and `observed_output.txt` contain the original submitted measurements.
Full Python implementation is in `../Docker_Kit/transactions.py` and `../Docker_Kit/lab10.py`.

From this folder, run a fresh experiment with Docker Desktop running:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

The launcher uses the exact published image and shared Exercise 10 replica set.
New JSON goes to `../Docker_Kit/results`; these original activity evidence files stay unchanged.
Use the root `DEMONSTRATE.ps1` for a complete fresh run and report.
