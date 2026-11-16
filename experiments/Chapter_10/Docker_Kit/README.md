# Exercise 10: Transactions, Atomicity, Durability & Journaling

A standalone MongoDB coursework project. It has its own Docker Compose project,
three MongoDB containers (`ex10-mongo1`, `ex10-mongo2`, `ex10-mongo3`), replica set
(`ex10`), network, volumes, and experiment databases. There is no Signal Desk
website, dependency, API, or production database connection.

## Start here — Windows PowerShell

1. Install/start Docker Desktop in Linux-container mode. You already have Docker from the previous exercises.
2. Extract this ZIP completely. Open the **Exercise_10_Transactions** folder that contains `compose.yaml` and `run-all.ps1` in VS Code or File Explorer.
3. Open PowerShell **in that folder**. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-all.ps1
```

The override applies only to that PowerShell process. Windows Python is not
required: Python, PyMongo, plotting and PDF generation run inside Docker.
Allow several minutes for the initial image download/build and experiments.
The lab intentionally causes write conflicts, failed transfers, and an unclean
restart of its own three containers. These are parts of the experiment. Its
MongoDB volumes are retained. No host database ports are published.

`run-all.ps1` builds the image, initializes the replica set, executes every lab,
checks committed data after restart, and creates the PDF, chart and transcript.
The first PDF is clearly marked DRAFT because a Docker Hub URL has not yet been supplied.

## What is implemented

| Task | Implementation and evidence |
| --- | --- |
| Lab 10.1: successful bank transfer | Two accounts; conditional debit, credit and history insert in one session/transaction |
| Insufficient funds | Rejected transfer; complete before/after account and history comparison |
| Atomic rollback after a write | Intentional exception after debit, before credit; neither account/history changes |
| Try It Yourself: conflict retries | A real competing version update forces a stale-snapshot write conflict; exponential backoff retries the entire transaction |
| Duplicate protection | A repeated transfer ID returns the already-committed result without a second transfer |
| Lab 10.2: reservation | Inventory decrement and pending order insert commit together |
| Contention | Eight simultaneous shoppers, five units; compare no retries with up to five retries |
| Throughput | 1, 4, 8 and 16 threads; 64 requests per trial, three repeats; transactional versus separate atomic stock update + order insert |
| Failure comparison | Intentional order-creation failure shows transactional rollback versus a stock decrement left without an order |
| Durability/journaling | Majority + j:true commit, unclean restart, new process IDs, both committed documents verified on every member |
| Results | Actual JSON evidence, readable terminal output, a throughput plot and a generated PDF |

The assignment's footer mentions "Lab-09" although its title/tasks are Exercise 10.
This project implements **Exercise 10**. MongoDB write conflicts are handled using
error labels (`TransientTransactionError`), not a nonexistent
`pymongo.errors.WriteConflict` class. An out-of-stock result is a business
rejection and is not retried unnecessarily. Unknown commit results retry only
the commit; they never blindly repeat the transfer.

## Open your results

After the run succeeds:

```powershell
notepad .\results\faculty-results.txt
Start-Process .\results\throughput.png
Start-Process .\results\Exercise_10_Report.pdf
```

| Generated file | Contents |
| --- | --- |
| `results/lab_10_1_bank.json` | Balances, history, rollback checks and real conflict retries |
| `results/lab_10_2_inventory.json` | Each scarcity request, repeat-by-repeat throughput, failure comparison |
| `results/lab_10_3_durability.json` | Before/after process IDs and document verification on all members |
| `results/faculty-results.txt` | Readable output to show faculty or capture in screenshots |
| `results/throughput.png` | Median successful reservations/second; error bars show min/max of three trials |
| `results/Exercise_10_Report.pdf` | Implementation, observed results, plot, evidence hashes and Docker Hub URL |

Output is generated from your machine. No measured results are pre-filled in
this ZIP. Successful throughput, conflict counts, and elected primaries vary.
A five-retry cap can be exhausted on a busy machine; inspect the actual results.
`expectedFiveReserved` records whether five succeeded and three were out of stock.
The publish script checks this before submission. Do not edit result JSON to
force a passing result. Repeated runs preserve prior result files in an archive
folder and use fresh experiment databases.

## Publish the completed Docker image

After the experiments succeed, run this with **your Docker Hub username**.
For your account:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\publish.ps1 -DockerHubUsername solankyyy
```

The script checks the result files, generates the report with your Docker URL,
builds a submission image containing `/evidence`, runs `docker login`, and pushes:

```text
solankyyy/exercise10-transactions:exercise10
```

The URL to place in the PDF is:

https://hub.docker.com/r/solankyyy/exercise10-transactions

**This is the intended new repository URL; it is not confirmed published until
`docker push` succeeds.** Make the Docker Hub repository public if faculty needs
to pull it. The initial report embeds the URL before the push; only submit it
once publication succeeds. If login or upload fails, fix that and rerun
`publish.ps1`; the experiments do not need to be rerun.

Submit **results/Exercise_10_Report.pdf** to Classroom. You may also send this
source ZIP if your instructor asks for implementation code. The Docker image is
the runnable artifact required for demonstration.

### Equivalent manual commands

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\make-report.ps1 -DockerHubUsername solankyyy
docker build -f Dockerfile.submission -t solankyyy/exercise10-transactions:exercise10 .
docker login
docker push solankyyy/exercise10-transactions:exercise10
```

`Dockerfile.submission` extends the local image built by `start.ps1`. It requires
the completed JSON, PDF, transcript and PNG files. The base `Dockerfile` builds
without any result files.

## Faculty demonstration — use the published image

The assignment explicitly requires demonstrating the uploaded Docker image.
On the demonstration machine with Docker Desktop running:

```powershell
docker pull solankyyy/exercise10-transactions:exercise10
docker create --name ex10-extract solankyyy/exercise10-transactions:exercise10
docker cp ex10-extract:/kit ./Exercise10_Demo
docker cp ex10-extract:/evidence ./Exercise10_Submitted_Evidence
docker rm ex10-extract
cd .\Exercise10_Demo
powershell -NoProfile -ExecutionPolicy Bypass -File .\demo-published.ps1 -Image solankyyy/exercise10-transactions:exercise10
```

This extracts the kit and original submitted evidence, then uses the **pulled
image** for every Python experiment without rebuilding it. Fresh demonstration
results go to `Exercise10_Demo/results`; submitted evidence remains separately
in `Exercise10_Submitted_Evidence`. Use an empty destination folder on the first
run. If a container named `ex10-extract` already exists, use a different extraction
name consistently in the three commands rather than overwriting someone else's container.

For the same machine, you can also run `demo-published.ps1` directly from the
original kit after publishing. Do not run two copies of the lab concurrently:
they intentionally use the same dedicated Exercise 10 container names.

## Run individual activities

First initialize/build once:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Then, as needed:

```powershell
docker compose run --rm -T python bank
docker compose run --rm -T python inventory
```

For the durability activity (only the dedicated Exercise 10 containers):

```powershell
docker compose run --rm -T python durability-prepare
docker compose kill -s SIGKILL ex10-mongo1 ex10-mongo2 ex10-mongo3
docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
docker compose run --rm -T python durability-verify
```

Verification fails if all three process IDs have not changed or either committed
document is missing. The automatic script restarts the nodes in a `finally`
block, including ordinary errors. If PowerShell or Docker is closed mid-test,
start Docker Desktop, run the `up -d` command above, and rerun the verifier.
Do not delete the volumes: they are what this durability experiment tests.

After all three JSON files exist, regenerate the report without rerunning:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\make-report.ps1 -DockerHubUsername solankyyy
```

To show the saved transcript in the terminal:

```powershell
Get-Content .\results\faculty-results.txt
```

To stop after finishing, preserving your data:

```powershell
docker compose stop
```

## Linux / macOS

```bash
bash run.sh
# After publishing, demonstrate the downloaded image without rebuilding:
EX10_IMAGE=solankyyy/exercise10-transactions:exercise10 bash run.sh https://hub.docker.com/r/solankyyy/exercise10-transactions
```

## File structure

| File | Responsibility |
| --- | --- |
| `transactions.py` | Transaction core, retry control, transfer and reservation functions |
| `lab10.py` | Database setup, measured experiments, invariant checks and CLI |
| `report.py` | Throughput calculations, chart, transcript and PDF |
| `test_transactions.py` | Unit tests for retry, commit, rollback and business-rule control flow |
| `compose.yaml` | Isolated replica set, Python service, network and volumes |
| `Dockerfile` | Builds the runnable lab and report tools; embeds `/kit` |
| `Dockerfile.submission` | Adds completed measurements/report under `/evidence` |
| `start.ps1` | Build and initialize |
| `run-all.ps1` | Full local build/run/report workflow |
| `run-experiments.ps1` | Experiments using the selected image |
| `make-report.ps1` | Generate a PDF from current results with a Docker Hub URL |
| `publish.ps1` | Validate evidence, build, log in and push the submission image |
| `demo-published.ps1` | Pull and demonstrate the published image |
| `run.sh` | Linux/macOS workflow |
| `IMPLEMENTATION.md` | Design decisions and validation boundaries |

## Validation

The 18 unit tests cover label-based retries, exponential delays, unknown-commit
handling, conditional writes, duplicate protection, and abort behavior. Run them
inside the image with:

```powershell
docker compose run --rm -T --entrypoint python python -m unittest -v test_transactions
```

Unit tests verify control flow and use mocked driver objects; they do not prove
live MongoDB atomicity. The live experiments independently inspect database
state and store explicit invariant checks. The preparation environment could not
start MongoDB (operation not permitted) and had no Docker Desktop/PowerShell,
so the complete container workflow still needs your local run. PDF layout was
checked using clearly labeled synthetic test data, which is not included as
submission evidence.

## References

- Assignment and samples: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-10
- PyMongo sessions/transactions: https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/
- Transaction error handling: https://www.mongodb.com/docs/manual/core/transactions-in-applications/

The attached faculty snippet is a starting point; this implementation additionally
checks update matches, uses versions and guarded writes, separates business
rejections from transient conflicts, and handles uncertain commits.
