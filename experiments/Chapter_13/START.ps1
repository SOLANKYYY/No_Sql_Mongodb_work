param([switch]$UsePublishedImage, [string]$Image='solankyyy/mongodb-exercise13:exercise13')
. "$PSScriptRoot/COMMON.ps1"
Docker-Ready
New-Item -ItemType Directory -Force results | Out-Null
if ($UsePublishedImage) {
    Set-LabImage $Image
    Run docker @('pull',$env:LAB_IMAGE)
} else {
    Set-LabImage 'exercise13-runner:local'
    Run docker @('build','-t',$env:LAB_IMAGE,'.')
}
Run docker @('run','--rm','--mount',"type=bind,source=$PSScriptRoot,target=/work",$env:LAB_IMAGE,'prepare')
Run docker @('compose','-f',$Compose,'config','--quiet')
foreach ($f in @('lab13_1_health.json','lab13_1_failover.json','lab13_1_monitoring.json','published.json','Exercise_13_Final_Report.pdf')) {
    Remove-Item "results/$f" -ErrorAction SilentlyContinue
}
Run docker @('compose','-f',$Compose,'up','-d','--wait','mongo1','mongo2','mongo3')
Run docker @('compose','-f',$Compose,'exec','-T','mongo1','mongosh','--quiet','--file','/scripts/bootstrap.js')
Run docker @('compose','-f',$Compose,'run','--rm','-T','runner','verify')
Write-Host 'SCREENSHOT 01: authenticated read/write, access denial, PRIMARY and two SECONDARY members above.'
Run docker @('compose','-f',$Compose,'run','--rm','-T','runner','failover')
Write-Host 'SCREENSHOT 02: old/new primary and successful post-stepdown samples above.'
Run docker @('compose','-f',$Compose,'up','-d','exporter','prometheus')
Run docker @('compose','-f',$Compose,'run','--rm','-T','runner','metrics')
Run docker @('compose','-f',$Compose,'ps')
Write-Host 'Lab 13.1 complete. Metrics: http://localhost:9216/metrics ; Prometheus: http://localhost:9090/targets'
Write-Host 'Next: enable Kubernetes in Docker Desktop; run LAB13_2.ps1. Screenshot guide: docs/SCREENSHOTS.md'
