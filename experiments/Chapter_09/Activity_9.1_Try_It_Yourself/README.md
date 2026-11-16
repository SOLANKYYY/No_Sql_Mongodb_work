# Activity_9.1_Try_It_Yourself

This folder contains the activity entrypoint and supporting code. The shared Docker setup is in `../Docker_Kit`. Preserve the complete extracted folder structure.

First run `start.ps1` from `Docker_Kit`. Then open PowerShell in this activity folder and run:

```powershell
docker compose run --rm -T --entrypoint python python /activity/try_9_1_journaling.py
```

Generated measurements are written to `../Docker_Kit/results/`. The journaling activity runs all six latency cases and replaces the latency JSON; it is not necessary to run it separately after Activity 9.1. For the simplest full workflow use the root README and run everything from Docker_Kit.
