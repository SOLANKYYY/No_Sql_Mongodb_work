# Troubleshooting

## Docker engine pipe / daemon unavailable
Open Docker Desktop, wait for Engine running, select Linux containers and run
`docker info`. Then rerun START.ps1. This is the same class of Docker-engine problem
that prevented a previous demonstration; no reinstall of this project is needed.

## PowerShell script blocked
Use `powershell -NoProfile -ExecutionPolicy Bypass -File .\START.ps1`.
This applies only to this PowerShell process. Extract the ZIP before running.

## Image download or pip install fails
Check Internet access, Docker proxy settings and registry sign-in. Repeat START.
Do not proceed to publication when a required command has failed.

## MongoDB does not become healthy
From the project folder:
```powershell
docker compose -f docker-compose-production.yml ps -a
docker compose -f docker-compose-production.yml logs --tail=60 key-init mongo1 mongo2 mongo3
```
Keep the original `.env` and `.secrets/keyfile` with existing data volumes. Generating
new passwords does not change users stored in those databases. A partial/missing
credential pair deliberately stops preparation. Do not delete data volumes as a
first troubleshooting step. The minimum MongoDB x86 CPU requirement includes AVX.

## Old 27017 conflict
This kit does not publish port 27017. It cannot conflict with a host MongoDB listener.
For occupied 9090 or 9216, stop the older monitoring stack or change only the host
side of the loopback port mapping and use that browser URL. Container checks still
use the original internal ports.

## Kubernetes context missing
Enable Kubernetes in Docker Desktop, wait for it to finish, and run:
```powershell
kubectl config get-contexts
kubectl --context docker-desktop cluster-info
```
The default script explicitly uses docker-desktop. Another local lab cluster can
be selected with `-KubeContext your-context`; inspect it before applying.

## Pending PVC or pod
```powershell
kubectl --context docker-desktop get storageclass
kubectl --context docker-desktop -n exercise13 get pods,pvc
kubectl --context docker-desktop -n exercise13 describe pod mongo-0
kubectl --context docker-desktop -n exercise13 get events --sort-by=.lastTimestamp
```
The cluster needs a default storage class that can provision three claims.
Pending pods may also indicate insufficient CPU/memory, image downloads or disk space.

## CrashLoopBackOff / authentication
```powershell
kubectl --context docker-desktop -n exercise13 logs mongo-0 -c prepare-key
kubectl --context docker-desktop -n exercise13 logs mongo-0 -c mongod --tail=60
```
All pods must use the SAME key. Do not replace the generated Secrets while existing
MongoDB data retains old users. Do not share kubectl get secret output.

## Failed pod recovery check
Inspect the saved output and get pods/PVCs. Wait for replication and rerun LAB13_2.
It should not claim success just because a pod is Running; it checks MongoDB roles,
data and original volume identities too.

## Docker Hub push denied
Confirm your username and repository ownership. Create mongodb-exercise13 under
that account, set it Public, and rerun PUBLISH.ps1 -DockerUser yourusername.
Use the Docker Hub interactive login flow or access token locally. Do not paste
the token into the chat. A push failure prevents final-report generation.

## What to send for debugging
Send the exact failing command and error text plus results ZIP, if available.
Never send passwords, keyfiles, API keys, .env, Secrets or Terraform state.
