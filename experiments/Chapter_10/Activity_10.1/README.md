# Activity_10.1

Bank transfer, insufficient funds, atomic rollback and duplicate protection.

`lab_10_1_bank.json` and `observed_output.txt` contain the original submitted measurements.
Full Python implementation is in `../Docker_Kit/transactions.py` and `../Docker_Kit/lab10.py`.

From this folder, run a fresh experiment with Docker Desktop running:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

The launcher uses the exact published image and shared Exercise 10 replica set.
New JSON goes to `../Docker_Kit/results`; these original activity evidence files stay unchanged.
Use the root `DEMONSTRATE.ps1` for a complete fresh run and report.
