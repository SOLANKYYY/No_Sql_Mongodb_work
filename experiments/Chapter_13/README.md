# Experiment 13 · Replica-set deployment with Compose and Kubernetes

Deploy a monitored replica set, observe a primary change, and check whether data survives Kubernetes pod replacement.

## Findings and evidence

The saved run observed the primary move from mongo1 to mongo2 and preserved acknowledged documents. On Kubernetes, the replacement pod had a new UID and reused the existing persistent volumes.

- [Election record](results/lab13_1_failover.json)
- [Pod and volume identifiers](results/lab13_2_kubernetes.json)
- [Chapter report](Exercise_13_Final_Report.pdf)

[All 18 experiments](../README.md)

---

Separate coursework project. This does not modify Signal Desk or its website.
Prepared against the instructor's Chapter 13 repository and both assignment screenshots.

## What to submit

1. Run Lab 13.1, monitoring and Lab 13.2 below.
2. Publish this project's Docker image to Docker Hub using PUBLISH.ps1.
3. Submit `results/Exercise_13_Final_Report.pdf` in Classroom. It contains your
   Docker URL, image tag/digest, actual results and an explanation of both labs.
4. Retain the image: the assignment says the uploaded Docker must be used for demonstration.

Do not submit the instructor's reference URLs as your own Docker submission.
The provided preparation PDF is NOT the final completed-lab report.
The final report is generated only after checks and image publication succeed.

## First run on Windows (PowerShell)

Extract the ZIP fully. Open the extracted `Exercise_13_Submission` folder, right-click
inside it and select Open in Terminal, or open PowerShell in that folder.
Do not run from inside the ZIP. Docker Desktop must be running Linux containers.
No host Python, mongosh, OpenSSL or MongoDB installation is needed.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\START.ps1
```

This builds the Python runner, generates local random credentials, prepares Linux
keyfile permissions inside a named volume, starts three data-bearing MongoDB nodes,
initializes rs0, creates admin/application/monitor users, verifies authentication,
runs a continuous PyMongo failover test, and checks Prometheus metrics.
It takes several minutes on first use while Docker downloads images.
No MongoDB host port is published, avoiding the earlier 27017 conflict.

## Kubernetes lab

Docker Desktop > Settings > Kubernetes > Enable Kubernetes > Apply/Restart.
Wait until Kubernetes is running. Reopen PowerShell if kubectl is not found.
Use Docker Desktop's default storage class; the lab requires three 1 GiB PVCs.
If resources are tight, pause other unrelated lab containers first.
You can also run STOP.ps1 after collecting the Compose screenshots to free memory
before the Kubernetes lab. Saved Compose results and database volumes are retained.

```powershell
kubectl config get-contexts
powershell -NoProfile -ExecutionPolicy Bypass -File .\LAB13_2.ps1
```

The script explicitly targets `docker-desktop` and namespace `exercise13`. It creates
a common Secret, headless Service, scripts ConfigMap and a 3-pod StatefulSet. Every
initContainer copies the SAME secret into its own memory-backed emptyDir, sets 0400
permissions and ownership, then MongoDB starts with keyFile authentication.
It bootstraps from mongo-0 over loopback, checks 1 PRIMARY + 2 SECONDARY members,
writes a sentinel with w=3, deletes mongo-2, waits for a different pod UID, verifies
the same PVC/PV identities, and reads the sentinel directly from recreated mongo-2.

## Publish, make final PDF, collect evidence

Create a public Docker Hub repository named `mongodb-exercise13` in your account.
Your earlier username is used as the default; use -DockerUser if it differs.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\PUBLISH.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\COLLECT.ps1
```

PUBLISH asks for name and roll number, checks all lab results, logs into Docker Hub,
builds the image WITH code and measured lab evidence, pushes and pulls it, records
the repository digest, and uses the published image to generate your final PDF.
Default image: `solankyyy/mongodb-exercise13:exercise13`.
Intended repository URL: https://hub.docker.com/r/solankyyy/mongodb-exercise13
This URL is a planned target until your push succeeds; it is not claimed to exist now.

Send `Exercise_13_Results.zip` and the screenshots listed in `docs/SCREENSHOTS.md`
back to the chat for review and, if desired, an illustrated report with screenshots.
The generated final PDF already contains the measured evidence and Docker URL.
Do not send `.env`, `.secrets`, Terraform state or credentials.

## Demonstrate using the published Docker image

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\DEMONSTRATE.ps1
```

This pulls the published image, exports its source to a new demonstration folder,
then runs both labs using that image (no runner source rebuild). If this folder
already has original credentials, they are reused to access the existing lab volumes.
Use this script from the original extracted folder, or use a clean Docker/Kubernetes
environment. Do not lose the credential files while retaining existing databases.
Official mongo and Prometheus images still provide their respective services.
All three database processes do NOT run inside a single container; Compose and
Kubernetes orchestrate them. The published image contains the executable tests,
source/manifests, supporting documents and completed result JSON files.

## Stop / resume

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\STOP.ps1
kubectl --context docker-desktop -n exercise13 scale statefulset mongo --replicas=0
```

Volumes and PVCs remain. START and LAB13_2 resume/recheck them using the original
credentials. No reset command is run automatically. Rerunning a lab invalidates
the previous publication/report metadata; publish again after the new run.

## Files

| Path | Purpose |
|---|---|
| docker-compose-production.yml | Authenticated rs0, three persistent MongoDB nodes, monitoring and test runner |
| scripts/bootstrap.js | Localhost initiation, first administrator, scoped users |
| scripts/lab.py | Credential preparation, health, authentication, PyMongo failover, exporter and metrics checks |
| k8s/*.yaml | Namespace, headless Service, ConfigMap, StatefulSet/PVCs/initContainer |
| scripts/k8s-check.js | Replication and direct sentinel read on recreated member |
| terraform/main.tf | Additional Atlas M0 infrastructure reference |
| scripts/report.py | Evidence validation and actual-result PDF generator |
| Dockerfile | Reproducible Python runner and distributable submission bundle |
| docs/SCREENSHOTS.md | Exact screenshots and where to obtain them |
| docs/TECHNICAL_REPORT.md | Design, comparison, limitations and reference corrections |
| docs/TROUBLESHOOTING.md | Windows/Docker/Kubernetes recovery steps |
| docs/VALIDATION.md | Checks actually performed during preparation |

Read `terraform/README.md` for the supplementary cloud configuration. Atlas is not
provisioned automatically and is not reported as deployed without evidence.

This is a production-oriented teaching deployment, not a complete production platform:
all local nodes share one machine, TLS/backups are not configured, and node/zone
failure isolation is not demonstrated. Credentials are generated per installation.
