# Methodology and assignment adaptations
## RAG
Five original teaching documents are split into at most 100-word chunks with 20-word overlap. MiniLM embeddings are 384-dimensional, normalized float vectors; the MongoDB index uses the actual dimension, not the screenshot's unrelated 1536-dimensional example. The same model embeds queries and stored passages. `$vectorSearch` returns top 3 with 60 candidates. FLAN-T5-small performs real local generation. Answers and queries are stored in MongoDB; the next prompt includes the last five exchanges, with bounded message lengths and no silent token truncation. The six-turn run checks that five exchanges enter the final prompt. Inspect output quality separately from pipeline success.
## Index comparison
FAISS HNSW uses M=16, efConstruction 32/64/128/256, efSearch 32/64/128. IVF uses nlist 50/100 and feasible nprobe 10/25/50/100. The 5,000 training sentences are generated text, not Wikipedia. Each receives a real MiniLM embedding. One hundred query texts are distinct from indexed documents. Both indexes use the same normalized vectors and inner product (equivalent to cosine ranking). Exact IndexFlatIP is ground truth; recall@20 = intersection size / 20. IVF build time includes training and adding vectors; HNSW includes adding vectors. Query times exclude embedding and setup and include single-query FAISS calls. Thread count is fixed at 2. Three warm-up queries precede measurement.
The MongoDB run uses the same corpus/queries, reports numCandidates 100/400/1000, and includes network/driver time. MongoDB index-ready wait is not reported as a comparable pure CPU build time. A reused ready index may make that wait short.
Atlas's documented schema supports HNSW/flat, not the assignment's IVF indexOption/nlists. This is an explicit adaptation: real MongoDB retrieval plus a separately labelled real FAISS HNSW-vs-IVF algorithm benchmark. Instructor acceptance of this adaptation may be needed; no unsupported Atlas command is disguised as working code.
## Interpretation
Choose a setting on the measured latency/recall frontier; no fixed winner or sample timings are pre-written. This is a small, single-host teaching corpus. It cannot establish production or million-vector performance. Higher efSearch/nprobe usually explores more candidates, but measured results determine the tradeoff here.
## References
- Instructor: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-17
- MongoDB vector index schema: https://www.mongodb.com/docs/vector-search/indexes/vector-search-type/
- Atlas Local Compose: https://www.mongodb.com/docs/atlas/cli/current/atlas-cli-docker-compose/
- FAISS indexes: https://github.com/facebookresearch/faiss/wiki/Faiss-indexes
- FastEmbed: https://qdrant.tech/documentation/embeddings/fastembed/
- Local generation model: https://huggingface.co/google/flan-t5-small
