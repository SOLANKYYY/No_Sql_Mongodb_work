# Exercise 9 implementation

## Implemented features

1. A separate three-member MongoDB 7 replica set, with persistent volumes and an isolated Docker network. The lab has no arbiter and publishes no host database ports.
2. Lab 9.1: 1,000 individual writes for each of six combinations of w=1, w=majority and w=3 with j=false/true. JSON evidence contains measured timings; the UI presents average, P50 and P99.
3. Journaling comparison using the same six benchmark cases. The assignment's all-members concern is implemented as numeric w=3.
4. Lab 9.2: healthy baseline, one-secondary isolation, recovery, two-secondary isolation and final recovery. The script records actual acknowledgments/errors, replica states and sentinel catch-up checks. PowerShell restores networking in its finally block.
5. Website imports with format/size/content validation and MongoDB persistence in exercise9_runs. Each activity retains its latest uploaded run.
6. An Exercise 9 page with benchmark comparisons, partition observations, recovery evidence, Docker kit download, Docker Hub URL and printable submission report.
7. Local and hosted HTTP routes, with the hosted application using its existing authentication.

## Code map

| Path | Responsibility |
| --- | --- |
| Docker_Kit/lab9.py | Replica-set initialization, benchmarks, partition observation and recovery verification |
| Docker_Kit/compose.yaml | Three MongoDB services, Python service, volumes and network |
| Docker_Kit/start.ps1 | Build image, start MongoDB and initialize replica set |
| Docker_Kit/run-partition.ps1 | Disconnect/reconnect lab containers and collect observations |
| Docker_Kit/Dockerfile | Runnable Python lab image |
| Docker_Kit/Dockerfile.submission | Extend image with the two measured result files |
| Signal_Desk_Source/backend/exercise9.py | Validate/import result JSON, retrieve runs and create downloadable kit |
| Signal_Desk_Source/backend/server.py | Local HTTP routes |
| Signal_Desk_Source/backend/web.py | Flask/cloud routes and authentication integration |
| Signal_Desk_Source/frontend/exercise9.js | Upload controls, tables, comparisons, timeline and printable report |
| Signal_Desk_Source/frontend/index.html | Page containers and sidebar navigation |
| Signal_Desk_Source/frontend/app.js | Page navigation integration |
| Signal_Desk_Source/frontend/styles.css | Page and print styling |
| Signal_Desk_Source/tests/test_exercise9.py | Exercise 9 validation, import, route and kit checks |
| Signal_Desk_Source/app.py, vercel.json, scripts/vercel_build.py | Hosted entrypoint and deployment/build configuration |

## API map

| Method/path | Purpose |
| --- | --- |
| GET /api/exercise9 | List saved run summaries |
| GET /api/exercise9/latency | Retrieve the latency run |
| GET /api/exercise9/partition | Retrieve the partition run |
| POST /api/exercise9/import | Validate and save a result JSON document |
| GET /api/exercise9/kit | Download the Docker lab kit |

## Boundaries

Docker performs the experiments on the local machine. Signal Desk stores and visualizes uploaded evidence; it does not execute Docker, disconnect production servers or measure live container status. Write-concern timeouts and election outcomes are displayed as observed, not replaced by theoretical expected results. Seed catalog data belongs to the existing application and is separate from Exercise 9 measurements.

## Source version

GitHub: https://github.com/SOLANKYYY/signal-desk

Packaged commit: a37fd3889f3a0d5e93e7e8c63fe443f581ddffcf

Packaging verification checks archive integrity and Python syntax. No new Docker, PowerShell, Atlas or Vercel execution is claimed by this package.
