# MongoDB Lab and Mini Project Submission

**Name:** Solanki Om Narendra  
**USN:** 24BTRCL190  
**Class:** AIML-B  
**Faculty:** Sujeet S Jagtap  
**Subject:** 23CSE528: NoSQL Database using MongoDB

## Reports for printing

- [Lab Experiments 01-18](reports/MongoDB_Lab_Experiments_01_to_18.pdf): one experiment per page, with Aim, Objective, Work Done / Procedure, Result and the available Docker Hub link. A consolidated Docker index follows the experiments.
- [Mini Project Report](reports/Signal_Desk_Mini_Project_Report.pdf): Building and Deploying an LLM/SLM-Backed Chat Application on MongoDB, using all eight required sections.

Print the two PDFs separately for submission.

## Folder guide

| Folder/file | What it contains and why |
|---|---|
| experiments/Chapter_01 to Chapter_18 | Each experiment keeps its code, datasets, original reports and evidence together, preserving relative paths. |
| mini-project/signal-desk | A source snapshot of the MongoDB-backed chat and threat-intelligence application. |
| reports | The two revised consolidated PDFs. |
| DOCKER_HUB_LINKS.md | Docker links and their publication evidence status. The same information is also in the lab PDF. |
| FILE_MANIFEST.json | File origins and checksums for the organised submission. |
| SUBMISSION_NOTES.md | Provenance, metadata corrections and evidence limitations. |

## Experiment index

| Chapter | Topic |
|---|---|
| [01](experiments/Chapter_01/) | NoSQL Database Models and Application Mapping |
| [02](experiments/Chapter_02/) | Environment Setup and CRUD Operations |
| [03](experiments/Chapter_03/) | Document Modelling, Validation and Large Objects |
| [04](experiments/Chapter_04/) | Query APIs, Updates and Bulk Operations |
| [05](experiments/Chapter_05/) | Aggregation Pipelines and Collection Joins |
| [06](experiments/Chapter_06/) | Indexing Strategies and Performance Tuning |
| [07](experiments/Chapter_07/) | Working Sets, Cache Behaviour and Schema Redesign |
| [08](experiments/Chapter_08/) | Replica Sets and Automatic Failover |
| [09](experiments/Chapter_09/) | Consistency, Write Concern and Network Partitions |
| [10](experiments/Chapter_10/) | Transactions, Concurrency and Durability |
| [11](experiments/Chapter_11/) | Sharding and Horizontal Scalability |
| [12](experiments/Chapter_12/) | Database Security and the CIA Triad |
| [13](experiments/Chapter_13/) | Container Orchestration and Persistent MongoDB Deployment |
| [14](experiments/Chapter_14/) | Monitoring, Backup and Restore |
| [15](experiments/Chapter_15/) | Secure Multi-Tenant Application APIs |
| [16](experiments/Chapter_16/) | Polyglot Persistence and a Hybrid Query Service |
| [17](experiments/Chapter_17/) | Vector Search and RAG Foundations |
| [18](experiments/Chapter_18/) | Comparative Threat-Intelligence Capstone |

## Running the work

Use the README, requirements and setup scripts inside the selected chapter. Configure private credentials locally; never commit .env files or private keys. Model downloads are intentionally excluded and can be obtained using Chapter 17 setup. Historical results are retained as supplied evidence; database workloads and Docker publication were not rerun during this packaging task.

Chapters 11 and 12 are included in the same numbered structure. Their original root folders remain on GitHub to preserve existing links. Chapter 15 duplicate nested ZIP content was deduplicated. Source code availability does not imply that every live test has been completed.

The current Signal Desk source supports provider-configurable chat. Chapter 17 supplies a separate local SLM demonstration with recorded answers, including weak outputs; those measurements do not certify the hosted chatbot.

Repository: https://github.com/SOLANKYYY/No_Sql_Mongodb_work
