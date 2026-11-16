param([Parameter(Mandatory=$true)][string]$Image)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
# The image must include a user/repository and explicit tag or digest.
if ($Image -notmatch '^[a-z0-9][a-z0-9_.-]*/exercise10-transactions(:[a-zA-Z0-9_.-]+|@sha256:[a-f0-9]{64})$') {
    throw 'Use USERNAME/exercise10-transactions:exercise10 (or its published digest).'
}
& docker pull $Image
if ($LASTEXITCODE -ne 0) { throw 'Could not pull the published image.' }
$LabPreviousImage = $env:EX10_IMAGE
try {
    $env:EX10_IMAGE = $Image
    New-Item -ItemType Directory -Force ./results | Out-Null
    & docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
    if ($LASTEXITCODE -ne 0) { throw 'Could not start replica set.' }
    Write-Host "Using published image: $Image (no image build)."
    $LabUser = $Image.Split('/')[0]
    & powershell -NoProfile -ExecutionPolicy Bypass -File ./run-experiments.ps1 -HubUrl "https://hub.docker.com/r/$LabUser/exercise10-transactions"
    if ($LASTEXITCODE -ne 0) { throw 'Published-image demonstration failed.' }
} finally {
    if ($null -eq $LabPreviousImage) { Remove-Item Env:EX10_IMAGE -ErrorAction SilentlyContinue }
    else { $env:EX10_IMAGE = $LabPreviousImage }
}
