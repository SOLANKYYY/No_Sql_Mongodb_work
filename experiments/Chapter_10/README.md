# Chapter 10 - Final Submission

Transactions, Atomicity, Durability & Journaling. Standalone Exercise 10 project.

## Submit

1. Upload **Chapter_10_Lab_Report.pdf** to Classroom. It contains the Docker Hub URL, implementation, observations, chart and evidence hashes.
2. Keep this complete ZIP for implementation review or attach it if faculty requests source code.
3. Demonstrate the published image using **DEMONSTRATE.ps1**.

Docker Hub: https://hub.docker.com/r/solankyyy/exercise10-transactions

Image tag: `solankyyy/exercise10-transactions:exercise10`

The package was assembled from `/kit` and `/evidence` in the published image at the digest in `DOCKER_HUB.txt`. Registry content hashes were verified. All recorded experiments are from your completed run; no new experiment has been invented or substituted.

## Folder format

| Folder / file | Contents |
| --- | --- |
| Activity_10.1 | Bank-transfer entry script, launcher, measured JSON and readable output |
| Activity_10.1_Try_It_Yourself | Retry exercise entry script, launcher and evidence from the same bank run |
| Activity_10.2 | Inventory entry script, launcher, measured JSON, output and throughput chart |
| Durability_and_Journaling | Restart-test launcher, original JSON and observed output |
| Docker_Kit | Complete published Python source, Dockerfiles, Compose configuration, PowerShell scripts, tests and results |
| Evidence | Unchanged published JSON/PDF/chart/transcript plus registry verification |
| Chapter_10_Lab_Report.pdf | PDF to submit |
| IMPLEMENTATION.md | Detailed implementation explanation |
| RESULTS_EXPLANATION.md | Explanation of the actual measured outcomes |
| DOCKER_HUB.txt | Repository URL, image tag and immutable digest |
| DEMONSTRATE.ps1 | Pull and run the exact uploaded image |
| SHOW-RESULTS.ps1 | Display saved output without running Docker |
| RUN-ACTIVITY.ps1 | Run one selected activity using the published image |
| SHA256SUMS.txt | Checksums for packaged files |

## Normal Windows PowerShell

Extract the ZIP. In PowerShell, move into the extracted folder that contains this README and DEMONSTRATE.ps1. If extracted directly into Downloads, use:

```powershell
cd "$env:USERPROFILE\Downloads\Chapter_10_Submission"
powershell -NoProfile -ExecutionPolicy Bypass -File .\SHOW-RESULTS.ps1
Start-Process .\Chapter_10_Lab_Report.pdf
```

If Windows created an extra outer folder, open the inner `Chapter_10_Submission` folder first. The path must contain `DEMONSTRATE.ps1`.

Your existing results are already included. You do not need to rerun Docker to submit the PDF.

## Demonstrate to faculty

Start Docker Desktop (Linux containers), then run from the submission root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\DEMONSTRATE.ps1
```

This pulls the exact published image, starts three dedicated Exercise 10 MongoDB nodes and performs all experiments. It does not build a replacement lab image. The durability test intentionally kills and restarts only those three nodes, retaining their volumes. Run only one Exercise 10 copy at a time because the container names are shared.

New measurements, chart and PDF go into `Docker_Kit/results`. The submitted records in `Evidence` and the root PDF remain unchanged. Prior working results are archived by the script.

To stop the lab and retain its data:

```powershell
cd .\Docker_Kit
docker compose stop
```

## Source and validation

The full implementation is centralized in Docker_Kit. Activity entry files organize the same implementation for submission. The kit README is preserved exactly as originally published and contains initial-build instructions; its statements about results not yet being generated/publication not yet verified describe that earlier source-only stage. For this completed package, follow this root README.

The published bank, inventory and durability JSON all report verification success. Packaging checks confirm those flags, expected five reservations, matching evidence hashes and complete ZIP contents. Unit tests validate transaction control flow; actual Docker experiments were run on your Windows machine. Fresh PowerShell/Docker execution was not repeated in the packaging environment.
