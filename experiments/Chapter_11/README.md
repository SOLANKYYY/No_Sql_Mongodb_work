# Experiment 11 · Sharding and shard-key selection

Compare timestamp range sharding with hashed user IDs and use query plans to see how many shards receive each query.

## Findings and evidence

The Docker lab defines two collections of 10,000 synthetic documents each and a separate customer-skew exercise. The validation notes record seven passing preparation tests. The repository contains a lab guide and test code, with live shard-distribution measurements pending.

- [Shard setup, distribution and routing checks](scripts/lab.py)
- [Validation status](docs/VALIDATION.md)
- [Lab guide](docs/Exercise_11_Lab_Guide.pdf)

[All 18 experiments](../README.md)

---

Solanki Om Narendra | 24BTRCL190 | 5AIMLB
23CSE528: NoSQL Database using MongoDB

## Start here

1. Start Docker Desktop and wait for Engine running. Linux containers are required.
2. Extract this ZIP. Open PowerShell in the folder that contains SETUP.ps1 (avoid an extra nested-folder mistake).
3. C: is supported. Moving this folder does not move Docker Desktop's image/volume storage.
4. Stop unused lab containers in Docker Desktop first to free RAM. Do not delete their volumes or images.
5. Run the following commands **one at a time**, continuing only after success:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1 -AllowSystemDrive
powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1
```

Save screenshots described in docs/SCREENSHOTS.md into screenshots/. Then:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\PUBLISH.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\COLLECT.ps1
```

PUBLISH asks you to sign in to Docker Hub as solankyyy. At Password paste a fresh Docker Hub access token with Read & Write permissions (nothing appears while typing). Never send the token in chat or put it in this folder. If authorization fails, use docker logout and docker login --username solankyyy, then rerun PUBLISH only. Set the repository visibility to Public in Docker Hub so the instructor can pull it.

## Files and separate Docker link

- Planned repository: https://hub.docker.com/r/solankyyy/nosql-exercise11
- Image: solankyyy/nosql-exercise11:exercise11
- Final PDF, created after successful run and verified push/pull: results/Exercise_11_Final_Report.pdf
- Final archive: Experiment_11_Completed_Submission.zip, beside SETUP.ps1.
- Actual measurements: results/evidence.json. No measured results are fabricated or shipped as yours.
- Read docs/Exercise_11_Lab_Guide.pdf now for theory, method and reporting details.

The repository URL is a target until PUBLISH succeeds. Docker Hub hosts a runnable container image, not a photo gallery or a ZIP download. It will show tags; screenshots go inside the PDF and completed ZIP. The push output digest and verified pull prove publication. Do not submit the pending-results guide as a completed report.

## Demonstrate the published image

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\DEMONSTRATE.ps1
```

Use the kit folder with docker-compose.yml. DEMONSTRATE pulls the tagged image, starts this kit's database services and reruns measurements. It does not require changing other labs. To stop only this lab and keep its data:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\STOP.ps1
```

If you add screenshots after publishing, run REPORT.ps1 then COLLECT.ps1. No new image push is needed for a PDF-only change. If source code or measured evidence changes, rerun PUBLISH.

## Troubleshooting

- Docker named-pipe error: Docker Desktop is stopped or starting. Wait, run docker info, then retry.
- Script not found: run Get-ChildItem and enter the folder containing SETUP.ps1.
- Dependency downloads: the Dockerfile uses the public PyPI index, isolated pip configuration and retries. A network failure still needs a working connection; do not change package versions blindly.
- Any test failure: stop and send the complete last error. Do not run PUBLISH/COLLECT until corrected.
- No destructive cleanup commands are required. RUN resets only this kit's isolated synthetic lab data.

See docs/VALIDATION.md for what was checked before delivery and what still requires your Docker run.
