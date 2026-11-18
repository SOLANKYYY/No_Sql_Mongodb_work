# Experiment 09 · Write concern, journaling and partitions

Compare the time required to acknowledge writes, then observe which writes can be acknowledged when replica-set members lose contact.

## Findings and evidence

The benchmark specifies 1,000 inserts for each of six write-concern and journal settings. The partition exercise disconnects one secondary and then both, and checks recovery on all three members. This folder contains the implementation. Its original README places the measured outputs in a separate submission archive.

- [Benchmark protocol](Docker_Kit/README.md)
- [Measurement implementation](Docker_Kit/lab9.py)
- [Partition and recovery procedure](Docker_Kit/run-partition.ps1)

## Activities

- [Activity_9.1](Activity_9.1/README.md)
- [Activity_9.1_Try_It_Yourself](Activity_9.1_Try_It_Yourself/README.md)
- [Activity_9.2](Activity_9.2/README.md)

[All 18 experiments](../README.md)

---

This is the separate code package for Signal Desk Exercise 9. It contains the complete application source and the Docker experiments. The report, recorded measurements and submission evidence are in the separate Chapter_09_Submission.zip.

## Folder guide

| Folder/file | Contents |
| --- | --- |
| Docker_Kit/ | Standalone runnable Exercise 9 Docker kit; start here for the experiments |
| Activity_9.1/ | Lab 9.1 latency entrypoint, matching the activity-folder layout |
| Activity_9.1_Try_It_Yourself/ | Journaling comparison entrypoint |
| Activity_9.2/ | Partition/recovery entrypoint and PowerShell launcher |
| Signal_Desk_Source/ | Complete website, backend, dependencies, tests, deployment configuration and lab kit |
| IMPLEMENTATION.md | What was implemented and the files responsible |
| FILE_LIST.txt | Every packaged file |
| SHA256SUMS.txt | Checksums of package contents |

The two Docker kit copies are intentionally identical: Docker_Kit is convenient for coursework, while Signal_Desk_Source/labs/chapter09 is needed by the website's kit-download endpoint. Run one copy only.

## Run the Docker experiments on Windows

Extract the whole ZIP, then open Docker_Kit in VS Code. With Docker Desktop running, execute these commands one at a time in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
docker compose run --rm -T python latency
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-partition.ps1
```

The commands generate:

- results/lab_9_1_latency.json
- results/lab_9_2_partition.json

The latency command also covers the Try It Yourself journaling comparison. You already completed these experiments; rerunning is only needed for a fresh demonstration. Your original results are in the separate submission package.

After both JSON files exist, the submission-image build is:

```powershell
docker build -f Dockerfile.submission -t solankyyy/signal-desk-exercise9:exercise9 .
```

Dockerfile.submission requires those generated results. It cannot build from this code-only ZIP before they exist. Your published image is already available at https://hub.docker.com/r/solankyyy/signal-desk-exercise9 and can be pulled using:

```powershell
docker pull solankyyy/signal-desk-exercise9:exercise9
```

For a demonstration using the published image, follow Docker_Kit/README.md, substituting solankyyy for YOUR_DOCKERHUB_USERNAME. Stop the lab when finished with `docker compose stop` from Docker_Kit.

## Run Signal Desk locally

Open PowerShell inside Signal_Desk_Source. Install Python 3.12+ if it is not already installed, then run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A running MongoDB database is required. If your existing local MongoDB already uses port 27017, use it. Otherwise, from Signal_Desk_Source start the application's bundled database with `docker compose up -d`. This database is separate from the three-node Exercise 9 lab.

```powershell
$env:MONGODB_URI = 'mongodb://127.0.0.1:27017'
$env:MONGODB_DB = 'signal_desk'
$env:AUTO_MONITOR = '0'
$env:AUTO_PROCESS_REPORTS = '0'
.\.venv\Scripts\python.exe -m backend.server
```

Open http://localhost:8000 and select Exercise 9 · Write concern. Upload the two generated JSON files using Upload results. This displays recorded experiments; it does not control laptop containers. The two optional AUTO settings above disable automatic background discovery and initial PDF processing for a focused lab demonstration.

For cloud setup use Signal_Desk_Source/docs/VERCEL_DEPLOYMENT.md. Extracting this ZIP does not redeploy the website. Supply your own database and application credentials through environment variables; they are not included.

## Check the implementation

From Signal_Desk_Source:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

This ZIP preserves the source; it is not a Docker image archive. Use Docker Hub to download the built image. Application seed catalog/BSON fixtures and documentation assets are included so the full application remains usable; generated experiment results, private settings and Git history are excluded.
