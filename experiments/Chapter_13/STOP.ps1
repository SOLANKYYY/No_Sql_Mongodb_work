. "$PSScriptRoot/COMMON.ps1"
Docker-Ready
Run docker @('compose','-f',$Compose,'down')
Write-Host 'Compose stopped; data volumes retained. Kubernetes is still running.'
Write-Host 'To pause Kubernetes: kubectl --context docker-desktop -n exercise13 scale statefulset mongo --replicas=0'
