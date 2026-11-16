# Exercise 13 - Technical report and explanation

## Objective and submission scope

Deploy and evaluate MongoDB using Docker Compose and Kubernetes. Lab 13.1 covers
three-node replication, keyfile authentication, a PyMongo failover demonstration,
and a Prometheus exporter. Lab 13.2 covers stable identities, persistent storage,
pod recreation and retained data. The reference main.tf is supplied as an additional
Atlas cloud configuration. This is independent of the earlier Signal Desk project.

The instructor requires a Docker Hub upload and a PDF containing the Docker URL.
The uploaded image must be usable for demonstration. Our image holds the runner,
all deployment source, documentation and measured JSON evidence. The image's export
command and DEMONSTRATE.ps1 reproduce the experiments through Compose and Kubernetes.

## Lab 13.1: deployment design

Three mongo:7.0 containers use rs0, authentication enforced by --keyFile, and separate
named data volumes. All three are data-bearing members, rather than two data members
and an arbiter. The first member initially has priority 2; the others have priority 1.
Service names mongo1, mongo2 and mongo3 remain stable inside the Compose network.
The runner executes in the same network, so replica discovery resolves these names.
No database host port is exposed. The exporter and Prometheus bind to loopback only.

The preparation command creates a 756-byte random secret encoded as base64, together
with random user passwords. A short-lived key-init container copies the key into a
Linux named volume, assigns UID/GID 999 and mode 0400. This avoids relying on Windows
bind-mount permission semantics. The same key is mounted read-only on every member.
Persisting .env and .secrets is necessary to reopen existing database volumes.

Initialization runs from inside mongo1 over localhost. It initiates rs0, waits for
that node to become primary, and creates the first administrator. The localhost
exception then closes. An authenticated replica-set connection creates labuser with
readWrite on exercise13 and monitor with clusterMonitor. Existing users are reused.
Protected collection access is tested without credentials and must fail with code
13. A successful unauthenticated ping alone would not prove authentication is off.

The application test writes a unique sentinel using w=3 and reads it back. Replica
status must show three healthy members, exactly one PRIMARY and two SECONDARY.
Evidence is saved to lab13_1_health.json. A failed assertion stops the workflow.

## PyMongo failover experiment

The runner keeps an application MongoClient alive while an observer repeatedly
performs majority-acknowledged writes and primary reads. A separate administrative
connection asks the current primary to step down for 60 seconds. The observer
continues during the election. Driver topology discovery selects the new primary.
Retries may hide a brief interruption; zero visible transient failures is valid.

The test records the old and new primary, observed election time, successful samples,
temporary failures and successful operations following the stepdown. It then checks
that all acknowledged documents still exist and that all three members are healthy.
It does not claim uninterrupted availability or zero election time. Actual values
come from the measured JSON, not from fixed illustrative output.

## Monitoring activity

A small Python Prometheus exporter accompanies mongo1. Its clusterMonitor user reads
serverStatus and replSetGetStatus. It exposes mongodb_up, connection counts,
cumulative operation counts and numeric member states. Prometheus scrapes it every
five seconds. Verification checks both the exporter endpoint and a Prometheus query,
so an HTTP server being reachable is not confused with MongoDB metrics being healthy.

The endpoint is http://localhost:9216/metrics and Prometheus is at
http://localhost:9090. State 1 indicates PRIMARY and state 2 SECONDARY. The exporter
tracks mongo1 directly; it can continue reporting when mongo1 becomes a secondary.
It is deliberately a small coursework exporter, not a full operational alerting suite.

## Lab 13.2: Kubernetes and storage

A dedicated namespace contains a headless Service, ConfigMap and StatefulSet.
The StatefulSet creates mongo-0 through mongo-2. Each pod has a distinct 1 GiB PVC.
The replica configuration uses their stable Service DNS names. Parallel pod startup
and publishNotReadyAddresses allow member discovery during bootstrap. Ping probes
test process responsiveness; the explicit lab checks establish replica-set health.

One generated key is stored in a Kubernetes Secret. Each initContainer copies that
same key into its pod-local memory-backed emptyDir, then sets ownership/permissions.
Generating a different random key separately in each pod would prevent authentication.
An emptyDir is shared by containers within a pod; it is not a cross-pod shared disk.
MongoDB data is stored in PVC-backed volumes, not in emptyDir.

The script initiates the replica set through kubectl exec inside mongo-0, creates the
users and waits for three healthy data members. It writes a persistence sentinel
with w=3, records mongo-2's UID and PVC/PV identities, deletes the pod and waits for a
new UID with Ready=True. The replacement must rejoin a healthy replica set and reuse
the same claims and volume bindings. A direct read from mongo-2 must return the
sentinel. Reading only from the primary would not demonstrate the recreated member
has the document. Kubernetes evidence is saved to lab13_2_kubernetes.json.

This demonstrates pod replacement with retained storage. It does not prove survival
of a destroyed disk, machine loss, or a multi-zone outage.

## Compose and Kubernetes comparison

| Aspect | Docker Compose | Kubernetes StatefulSet |
|---|---|---|
| Identity | Stable service DNS on the Compose network | Stable ordinal pod names and headless-Service DNS |
| Storage | One named volume per MongoDB service | One PVC per StatefulSet replica |
| Process recovery | Restart policy restarts failed containers | Kubelet restarts containers; controller replaces missing pods |
| Removed instance | Compose up reconciles missing services | StatefulSet automatically restores the desired pod count |
| Member election | MongoDB replica-set protocol | MongoDB replica-set protocol |
| Configuration | Simpler local multi-container file | Service, StatefulSet, Secrets, ConfigMap, PVCs and cluster context |
| Tested failure | Planned primary stepdown | Deletion and recreation of one pod |

Both approaches require reachable member hostnames, matching keys and independent
data directories. Kubernetes does not itself elect the MongoDB primary.

## Cloud reference

terraform/main.tf declares a separate Atlas project, M0 tenant cluster, database user
and specific client-IP access entry. Credentials come from environment variables.
The configuration uses provider v2 advanced_cluster syntax, leaves M0-managed
version/storage settings to Atlas, and avoids embedding credentials in outputs.
Terraform validate checks configuration; plan previews actions; apply provisions them.
These are distinct evidence levels. The supplied package does not claim any cloud
resource was created. See terraform/README.md for local instructions.

## Corrections to the teaching reference

The instructor scripts are reference material, and the screenshots are the task
requirements. This implementation retains the objectives while correcting:

- Bootstrap order: initiate, elect a primary, then create the first user through localhost.
- Shared authentication key: use one Secret across pods, not separately generated emptyDirs.
- Replica membership: three data-bearing nodes for the required primary/secondary checks.
- Hostname routing: run PyMongo in the same network as the advertised member names.
- Authentication proof: test a protected read; ping is not a valid access-denial test.
- Storage and resiliency proof: new pod UID, same PVC/PV, sentinel on the recreated member.
- Cloud configuration: updated M0 provider syntax and scoped access without a duplicated URI prefix.
- Reporting: never count generated manifests or a successful plan as a completed deployment.

## Limitations and conclusion

The setup adds authentication, persistent volumes, restart behavior, bounded logs,
resource controls and monitoring to a classroom replica set. A real production
deployment also needs TLS, backups and restore tests, stronger isolation, secret
rotation, upgrade policy and operational alerting. Three local containers or pods
share a physical failure domain. Report conclusions are conditional on actual checks;
the final report generator refuses missing or failed required evidence.

## References consulted

1. Instructor Chapter 13: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/tree/main/chapter-13
2. Compose reference: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/blob/main/chapter-13/docker-compose-production.yml
3. Terraform reference: https://github.com/sujeetjagtap/NoSQL-Databases-using-MongoDB/blob/main/chapter-13/main.tf
4. MongoDB keyfile deployment: https://www.mongodb.com/docs/manual/tutorial/deploy-replica-set-with-keyfile-access-control/
5. MongoDB localhost exception: https://www.mongodb.com/docs/manual/core/localhost-exception/
6. StatefulSets: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
7. Kubernetes volumes: https://kubernetes.io/docs/concepts/storage/volumes/
8. Atlas Terraform provider: https://registry.terraform.io/providers/mongodb/mongodbatlas/latest/docs/resources/advanced_cluster
9. Atlas free-cluster limits: https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/
