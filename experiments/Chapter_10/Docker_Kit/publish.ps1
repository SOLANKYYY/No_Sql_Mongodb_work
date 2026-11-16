param([Parameter(Mandatory=$true)][string]$DockerHubUsername)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if ($DockerHubUsername -notmatch '^[a-z0-9][a-z0-9_-]*$') { throw 'Enter your Docker Hub username only.' }
$LabRequired = @('lab_10_1_bank.json','lab_10_2_inventory.json','lab_10_3_durability.json')
foreach ($LabFile in $LabRequired) {
    $LabPath = Join-Path ./results $LabFile
    if (-not (Test-Path $LabPath)) { throw "Missing $LabPath. Run run-all.ps1 first." }
    $LabResult = Get-Content $LabPath -Raw | ConvertFrom-Json
    if ($LabResult.verified -ne $true) { throw "$LabFile has an unsuccessful invariant check. Inspect it before submitting." }
}
$LabInventory = Get-Content ./results/lab_10_2_inventory.json -Raw | ConvertFrom-Json
if ($LabInventory.expectedFiveReserved -ne $true) { throw 'The five-reservations/three-out-of-stock goal was not observed. Inspect the results and retry the inventory experiment.' }
& powershell -NoProfile -ExecutionPolicy Bypass -File ./make-report.ps1 -DockerHubUsername $DockerHubUsername
if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
$LabImage = "$DockerHubUsername/exercise10-transactions`:exercise10"
& docker build -f Dockerfile.submission -t $LabImage .
if ($LASTEXITCODE -ne 0) { throw 'Submission image build failed.' }
& docker login
if ($LASTEXITCODE -ne 0) { throw 'Docker Hub login failed.' }
& docker push $LabImage
if ($LASTEXITCODE -ne 0) { throw 'Docker push failed; the image is not confirmed published.' }
Write-Host "Published $LabImage"
Write-Host "Docker URL: https://hub.docker.com/r/$DockerHubUsername/exercise10-transactions"
Write-Host 'Submit results/Exercise_10_Report.pdf. See README for demonstrating the PULLED image.'
