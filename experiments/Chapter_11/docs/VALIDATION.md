# Validation and scope

Before delivery: Python source compiled; unit tests cover shard explain parsing and customer skew (11), and real certificate signatures/SAN plus precise authorization-error handling (12). Compose YAML parsed. PDF guides rendered and reviewed. Report validation rejects missing/failed evidence and malformed publication metadata.

This workspace has no Docker daemon. A native MongoDB 7.0.16 startup attempt was blocked by the runtime with "open: Operation not permitted" before accepting connections. Therefore live MongoDB integration, Docker Compose startup and Docker Hub publication could not be completed here. SETUP and RUN perform those checks on your Docker Desktop; PUBLISH refuses to proceed without measured successful evidence. These tests do not claim a completed live lab.

Pinned MongoDB 7.0.16 is an educational reproducibility baseline, not a recommendation to deploy this patch release to production. Both labs use synthetic data and private Compose networks, with no host database ports exposed. No production data or existing lab volumes are altered.

Validation suite: 7 tests passed, including publication URL/digest typing and refusal to report a failed or missing run.
