# Experiment 18: Comparative Threat Intelligence Capstone

Student: Solanki Om Narendra | Roll: 24BTRCL190

This is a separate submission kit. Intended image: `solankyyy/nosql-exercise18:exercise18`.
Intended repository: https://hub.docker.com/r/solankyyy/nosql-exercise18
The link becomes a published submission only after PUBLISH.ps1 succeeds. This download contains no invented successful results.

## Run on Windows
1. Extract this ZIP. Open the folder containing SETUP.ps1 (avoid the outer extraction folder).
2. Open Docker Desktop with Linux containers. Stop experiments 13-16 to release RAM, preserving their volumes.
3. Open PowerShell in this folder. Run ONE command at a time; stop on any error:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\SPACE_CHECK.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1 -AllowSystemDrive
powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\PUBLISH.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\COLLECT.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\STOP.ps1
```

SETUP uses C: if that is where you extracted it. It never requires E:. Docker images/volumes remain in Docker Desktop's disk; moving just this folder does not move them. There is no automatic deletion or global Docker prune.

## Deliverables
- `results/Exercise_18_Final_Report.pdf`: final report with measured results and verified Docker link, generated after publish.
- `Experiment_18_Completed_Submission.zip`: code, docs, measured evidence, report and your screenshots.
- `results/evidence.json`: raw measurement summary. Do not edit values to mark a failed run as passed.
- `results/published.json`: exact pulled image digest; digest parsing avoids the older PowerShell JSON-array bug.

The initial PDF in docs is a preparation guide, not a completed experiment report. Final report generation is blocked until the run passes and image publication is verified.

## Screenshots
Save actual PNG/JPG screenshots into screenshots/. Run REPORT.ps1 again to embed them, then COLLECT.ps1 again. Docker Hub is an image registry, not a screenshot gallery; screenshots belong in the PDF/ZIP. No screenshots are fabricated.

## Demonstrate the uploaded image
Run DEMONSTRATE.ps1 from this same kit. It pulls the published image and uses it for the lab runner. Internet may be required for dependencies/models; input data requirements still apply. Final result summaries are also included at `/kit/results/evidence.json` inside the published image. To inspect them without rerunning:

```powershell
docker run --rm --entrypoint python solankyyy/nosql-exercise18:exercise18 -m json.tool /kit/results/evidence.json
```

## Limits and references
Live container execution must be verified on your Windows Docker host. Preparation checks are not measured database evidence. Images use version tags; actual engine/package versions are captured by the run.
Instructor: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-18
See docs/METHODOLOGY.md and docs/SCREENSHOTS.md.

## Included real dataset and reduced workload
This revision includes 15,000 public MISP indicator observations in `data/threats.jsonl`, plus provenance in `data/source.json`. No API credentials or further data download are required. They represent five source events from three publishers, not 15,000 confirmed incidents. Most observations are from one publisher; the benchmark is not a representative global threat sample.

The assignment originally required 100,000 records. At your request this version measures up to 15,000 and explicitly discloses that adaptation. It does not claim full compliance with the original volume. The final PDF uses the actual measured count.

If updating your existing folder, extract this ZIP into it and replace matching code files. Your `.env` is not included or overwritten. Then run SETUP again (the successful isolated-PyPI installation fix is included), followed by RUN. Run PUBLISH and COLLECT only after RUN passes.

Public input is included in the Docker build and completed ZIP for demonstration. Do not replace it with private data before publishing. Source semantics and limitations are in docs/METHODOLOGY.md.
