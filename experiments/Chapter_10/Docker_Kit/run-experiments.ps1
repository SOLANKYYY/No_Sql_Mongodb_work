param([string]$HubUrl = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Invoke-Exercise10([string[]]$LabArgs) {
    & docker compose run --rm -T python @LabArgs
    if ($LASTEXITCODE -ne 0) { throw "Exercise 10 command failed: $LabArgs" }
}
# Preserve previous outputs before beginning a new batch.
if (Test-Path ./results/lab_10_1_bank.json) {
    $LabBackup = Join-Path ./results ('archive-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Force $LabBackup | Out-Null
    Get-ChildItem ./results -File | Copy-Item -Destination $LabBackup
}
Invoke-Exercise10 -LabArgs @('init')
Invoke-Exercise10 -LabArgs @('bank')
Invoke-Exercise10 -LabArgs @('inventory')
Invoke-Exercise10 -LabArgs @('durability-prepare')
Write-Host 'Durability test: unclean restart of the THREE EXERCISE 10 containers. Volumes are preserved.'
try {
    & docker compose kill -s SIGKILL ex10-mongo1 ex10-mongo2 ex10-mongo3
    if ($LASTEXITCODE -ne 0) { throw 'Could not interrupt the Exercise 10 nodes.' }
} finally {
    & docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
    if ($LASTEXITCODE -ne 0) { throw 'Restart failed. Run docker compose up -d for these three nodes and then verify.' }
}
Invoke-Exercise10 -LabArgs @('durability-verify')
$LabReportArgs = @('report')
if ($HubUrl) { $LabReportArgs += @('--hub-url', $HubUrl) }
Invoke-Exercise10 -LabArgs $LabReportArgs
Write-Host 'Finished. Open results/Exercise_10_Report.pdf and results/faculty-results.txt.'
