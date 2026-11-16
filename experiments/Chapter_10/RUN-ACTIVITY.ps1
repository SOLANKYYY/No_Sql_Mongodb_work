param([Parameter(Mandatory=$true)][ValidateSet('bank','inventory','durability')][string]$Activity)
$ErrorActionPreference = 'Stop'
$LabOriginalImage = $env:EX10_IMAGE
Push-Location (Join-Path $PSScriptRoot 'Docker_Kit')
function Invoke-Lab([string]$Action) {
    & docker compose run --rm -T python $Action
    if ($LASTEXITCODE -ne 0) { throw "Lab command failed: $Action" }
}
try {
    $env:EX10_IMAGE = 'solankyyy/exercise10-transactions@sha256:a7cb4c956e7fd866ecdbedd534699a3cdbace4d472b8ffa33fe273b72e0c5e2e'
    & docker pull $env:EX10_IMAGE
    if ($LASTEXITCODE -ne 0) { throw 'Image download failed.' }
    New-Item -ItemType Directory -Force './results' | Out-Null
    $LabArchive = Join-Path './results' ('archive-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    New-Item -ItemType Directory -Force $LabArchive | Out-Null
    Get-ChildItem './results' -File | Copy-Item -Destination $LabArchive
    & docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
    if ($LASTEXITCODE -ne 0) { throw 'Replica set startup failed.' }
    Invoke-Lab 'init'
    if ($Activity -eq 'durability') {
        Invoke-Lab 'durability-prepare'
        try {
            & docker compose kill -s SIGKILL ex10-mongo1 ex10-mongo2 ex10-mongo3
            if ($LASTEXITCODE -ne 0) { throw 'Container interruption failed.' }
        } finally {
            & docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
            if ($LASTEXITCODE -ne 0) { throw 'Restart failed; start the three Exercise 10 nodes before verification.' }
        }
        Invoke-Lab 'durability-verify'
    } else { Invoke-Lab $Activity }
    Write-Host 'New JSON is in Docker_Kit/results. Original submitted evidence remains in Evidence.'
    Write-Host 'Use DEMONSTRATE.ps1 for a complete new run and matching report.'
} finally {
    Pop-Location
    if ($null -eq $LabOriginalImage) { Remove-Item Env:EX10_IMAGE -ErrorAction SilentlyContinue }
    else { $env:EX10_IMAGE = $LabOriginalImage }
}
