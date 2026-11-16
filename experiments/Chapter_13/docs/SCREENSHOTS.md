# Screenshots to send after running

Save screenshots using the suggested names below. Include the command and useful
result lines; avoid tiny full-terminal captures. Capture multiple images if needed.
Do not show .env, Secrets, passwords, API keys, docker login tokens or Terraform state.

| Name | Where and exact content |
|---|---|
| 01-compose-health.png | PowerShell after START.ps1: PRIMARY + SECONDARY + SECONDARY, authenticated_read_write=true and unauthenticated_read_denied=true. |
| 02-failover.png | PowerShell: old_primary, different new_primary, post_stepdown_successes > 0, acknowledged_documents_preserved=true, passed=true. |
| 03a-exporter.png | Browser http://localhost:9216/metrics : mongodb_up 1.0 and mongodb_member_state lines. |
| 03b-prometheus.png | Browser http://localhost:9090/targets : mongodb target UP. On the query page also run mongodb_up and capture value 1. |
| 04-kubernetes-before.png | PowerShell LAB13_2.ps1 output: 3 pods 1/1 Running and 3 PVCs Bound, followed by healthy replica members. |
| 05-kubernetes-recovery.png | PowerShell: different old_pod_uid/new_pod_uid, persistent_volumes_reused=true, sentinel=survives-pod-recreation and passed=true. |
| 06-dockerhub.png | Docker Hub > mongodb-exercise13 > Tags: exercise13 tag, username/repository visible. Also capture the terminal's PUBLISHED and DOCKER URL lines. |

If you missed the terminal output, use these commands from the project folder:

```powershell
Get-Content .\results\lab13_1_health.json
$f = Get-Content .\results\lab13_1_failover.json -Raw | ConvertFrom-Json
$f | Select-Object old_primary,new_primary,election_observed_seconds,post_stepdown_successes,acknowledged_documents_preserved,passed | Format-List
kubectl --context docker-desktop -n exercise13 get pods -o wide
kubectl --context docker-desktop -n exercise13 get pvc
Get-Content .\results\lab13_2_kubernetes.json
Get-Content .\results\published.json
```

The before-deletion pod UID and PVC identifiers are retained inside the Kubernetes
JSON; the later get-pods command shows current state only.
The results files are the primary measured evidence. Screenshots illustrate them.

Additional Atlas screenshots ONLY if you run the cloud section:
terraform validate; non-sensitive terraform plan summary; deployed M0 cluster page.
A Terraform plan must be labelled planned, not deployed.

Finally:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\COLLECT.ps1
```

Upload Exercise_13_Results.zip and the screenshots to the chat. Classroom receives
the final PDF with your Docker URL, as stated in the assignment.
