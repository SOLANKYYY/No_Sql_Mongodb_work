param([string]$KubeContext='docker-desktop', [string]$Image='exercise13-runner:local')
. "$PSScriptRoot/COMMON.ps1"
Docker-Ready
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) { throw 'Enable Kubernetes in Docker Desktop and reopen PowerShell.' }
$K = @('--context',$KubeContext,'--namespace','exercise13')
Run kubectl @('--context',$KubeContext,'cluster-info')
Run docker @('run','--rm','--mount',"type=bind,source=$PSScriptRoot,target=/work",$Image,'prepare')
New-Item -ItemType Directory -Force results | Out-Null
Remove-Item results/lab13_2_kubernetes.json -ErrorAction SilentlyContinue
Remove-Item results/published.json -ErrorAction SilentlyContinue
Remove-Item results/Exercise_13_Final_Report.pdf -ErrorAction SilentlyContinue
Run kubectl @('--context',$KubeContext,'apply','-f','k8s/00-namespace.yaml')
Run kubectl @('--context',$KubeContext,'apply','-f','.secrets/k8s-secrets.json')
Run kubectl @('--context',$KubeContext,'apply','-f','k8s/01-headless-service.yaml','-f','k8s/02-scripts.yaml','-f','k8s/03-statefulset.yaml')
Run kubectl ($K + @('rollout','status','statefulset/mongo','--timeout=600s'))
Run kubectl ($K + @('exec','mongo-0','-c','mongod','--','mongosh','--quiet','--file','/scripts/bootstrap.js'))
function Mongo-Check {
    param([string]$Action)
    $deadline = (Get-Date).AddSeconds(180)
    do {
        $out = & kubectl @K exec mongo-0 -c mongod -- env "CHECK_ACTION=$Action" mongosh --quiet --file /scripts/k8s-check.js
        if ($LASTEXITCODE -eq 0) { return (($out -join "`n") | ConvertFrom-Json) }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)
    throw 'Kubernetes database checks failed; inspect pods and logs using docs/TROUBLESHOOTING.md.'
}
$before = Mongo-Check 'seed'
$podBefore = (Run kubectl ($K + @('get','pod','mongo-2','-o','json')) -Capture) -join "`n" | ConvertFrom-Json
$pvcsBefore = (Run kubectl ($K + @('get','pvc','-o','json')) -Capture) -join "`n" | ConvertFrom-Json
Run kubectl ($K + @('get','pods','-o','wide'))
Run kubectl ($K + @('get','pvc'))
$before | ConvertTo-Json -Depth 8 | Write-Host
Write-Host 'SCREENSHOT 04: three ready pods, bound PVCs and healthy MongoDB members above.'
Run kubectl ($K + @('delete','pod','mongo-2','--wait=true','--timeout=120s'))
$deadline = (Get-Date).AddSeconds(300)
$podAfter = $null
do {
    $raw = & kubectl @K get pod mongo-2 -o json --ignore-not-found
    if ($LASTEXITCODE -ne 0) { throw 'Unable to query recreated pod.' }
    if ($raw) {
        $candidate = ($raw -join "`n") | ConvertFrom-Json
        $ready = @($candidate.status.conditions | Where-Object { $_.type -eq 'Ready' -and $_.status -eq 'True' }).Count -gt 0
        if ($candidate.metadata.uid -ne $podBefore.metadata.uid -and $ready) { $podAfter = $candidate; break }
    }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)
if (-not $podAfter) { throw 'A new ready mongo-2 pod was not observed within 300 seconds.' }
$after = Mongo-Check 'status'
$pvcsAfter = (Run kubectl ($K + @('get','pvc','-o','json')) -Capture) -join "`n" | ConvertFrom-Json
$storage = @()
foreach ($old in $pvcsBefore.items) {
    $new = @($pvcsAfter.items | Where-Object { $_.metadata.name -eq $old.metadata.name })
    if ($new.Count -ne 1) { throw 'PVC disappeared during recovery.' }
    $storage += [ordered]@{ name=$old.metadata.name; uid_before=$old.metadata.uid; uid_after=$new[0].metadata.uid;
        volume_before=$old.spec.volumeName; volume_after=$new[0].spec.volumeName; phase=$new[0].status.phase }
}
$sameStorage = $storage.Count -eq 3 -and @($storage | Where-Object {
    $_.uid_before -ne $_.uid_after -or $_.volume_before -ne $_.volume_after -or $_.phase -ne 'Bound'
}).Count -eq 0
$result = [ordered]@{ lab='13.2'; timestamp=[DateTime]::UtcNow.ToString('o'); context=$KubeContext;
    passed=($after.passed -and $sameStorage -and ($podBefore.metadata.uid -ne $podAfter.metadata.uid));
    pod_name='mongo-2'; old_pod_uid=$podBefore.metadata.uid; new_pod_uid=$podAfter.metadata.uid;
    persistent_volumes_reused=$sameStorage; storage=$storage; before=$before; after=$after }
Save-Json 'results/lab13_2_kubernetes.json' $result
Run kubectl ($K + @('get','pods','-o','wide'))
Run kubectl ($K + @('get','pvc'))
$result | ConvertTo-Json -Depth 15 | Write-Host
if (-not $result.passed) { throw 'Recovery evidence failed validation.' }
Write-Host 'SCREENSHOT 05: new pod UID, same PVCs, sentinel read from mongo-2, and passed=true.'
Write-Host 'Lab 13.2 complete. Next: PUBLISH.ps1, then COLLECT.ps1.'
