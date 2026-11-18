# Experiment 17 · Vector search and retrieval-augmented answers

Retrieve passages for a question-answering application and measure how vector-search settings affect latency and recall.

## Findings and evidence

The local RAG run indexed 10 chunks from five documents. A separate benchmark used 5,000 generated sentences and 100 queries. On MongoDB Atlas Local, 400 candidates gave recall@20 of 1.00 against exact search in that run.

- [RAG source documents](data/documents.json)
- [Benchmark design](docs/METHODOLOGY.md)
- [Answers and measurements](results/evidence.json)
- [Latency and recall plot](results/latency_recall.png)

[All 18 experiments](../README.md)

---

Student: Solanki Om Narendra | Roll: 24BTRCL190

This is a separate submission kit. Intended image: `solankyyy/nosql-exercise17:exercise17`.
Intended repository: https://hub.docker.com/r/solankyyy/nosql-exercise17
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
- `results/Exercise_17_Final_Report.pdf`: final report with measured results and verified Docker link, generated after publish.
- `Experiment_17_Completed_Submission.zip`: code, docs, measured evidence, report and your screenshots.
- `results/evidence.json`: raw measurement summary. Do not edit values to mark a failed run as passed.
- `results/published.json`: exact pulled image digest; digest parsing avoids the older PowerShell JSON-array bug.

The initial PDF in docs is a preparation guide, not a completed experiment report. Final report generation is blocked until the run passes and image publication is verified.

## Screenshots
Save actual PNG/JPG screenshots into screenshots/. Run REPORT.ps1 again to embed them, then COLLECT.ps1 again. Docker Hub is an image registry, not a screenshot gallery; screenshots belong in the PDF/ZIP. No screenshots are fabricated.

## Demonstrate the uploaded image
Run DEMONSTRATE.ps1 from this same kit. It pulls the published image and uses it for the lab runner. Internet may be required for dependencies/models; input data requirements still apply. Final result summaries are also included at `/kit/results/evidence.json` inside the published image. To inspect them without rerunning:

```powershell
docker run --rm --entrypoint python solankyyy/nosql-exercise17:exercise17 -m json.tool /kit/results/evidence.json
```

## Limits and references
Live container execution must be verified on your Windows Docker host. Preparation checks are not measured database evidence. Images use version tags; actual engine/package versions are captured by the run.
Instructor: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-17
See docs/METHODOLOGY.md and docs/SCREENSHOTS.md.

## Exercise 17 details
- First run downloads real MiniLM 384-dimensional embeddings and FLAN-T5-small generation weights into .cache/. No API key is required; model quality is limited and answers need review.
- MongoDB Atlas Local includes mongod + mongot. This is a local development deployment, not a hosted Atlas cloud cluster. Set MONGO_URI privately in .env to use your own Atlas cluster if required. The default run still starts the local service; stop it separately if using Atlas.
- 5 original teaching documents, 100-word sliding chunks, top-3 `$vectorSearch`, and six dialogue turns prove the last-five-exchange memory behavior.
- 5,000 generated training sentences have real 384-D embeddings. FAISS implements real multi-layer HNSW and IVF; 100 held-out query texts use exact top-20 ground truth. MongoDB HNSW is additionally benchmarked separately.
- The assignment's Atlas IVF / indexOption configuration is not supported by the documented Atlas index schema. This kit clearly records that adaptation. Do not present FAISS latency as Atlas latency.
- Reserve roughly 6-10 GB free disk for first-run images/models/cache and at least 6 GB available Docker RAM; actual downloads vary. Stop heavy previous labs first.

Ask your own question after RUN succeeds:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ASK.ps1 -Question "Why should analysts correlate independent evidence?"
```
