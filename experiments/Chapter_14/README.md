# Experiment 14 - standalone submission
Solanki Om Narendra | 24BTRCL190

This folder is independent. It has its own code, Docker Compose project (experiment14), volumes, results, report and Docker Hub repository. No other experiment's results are required.

Extract onto E: and open PowerShell in this folder. Move Docker Desktop disk image storage to E: separately; see docs/E_DRIVE_SETUP.md. Stop previously running labs to save RAM.

Run in this order, one command at a time:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\PUBLISH.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\COLLECT.ps1
```

PUBLISH uploads only solankyyy/nosql-exercise14:exercise14 and generates results/Exercise_14_Final_Report.pdf after recorded checks pass. Set https://hub.docker.com/r/solankyyy/nosql-exercise14 to Public after publication. Submit this experiment's final PDF and retain this folder for demonstration.

DEMONSTRATE.ps1 pulls this experiment's published image and reruns only this experiment. STOP.ps1 preserves volumes. No results or publishing have been fabricated; live Docker/PowerShell execution must be performed on your computer.

If migrating from the old combined kit: copy only results/lab14_*.json into this folder's results if already successfully generated. Preserve the old kit and its .env separately; these standalone projects use new volumes. Do not delete previous data. Existing measured results can be published without rerunning labs after SETUP, but the standalone database starts empty until RUN is executed.

The local database services are classroom configurations with no database authentication and no public network binding. This is not a hardened public production deployment.

Reference: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-14
