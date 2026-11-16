$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force ./results | Out-Null
if ($env:EX10_IMAGE -and $env:EX10_IMAGE -ne 'exercise10-transactions:local') {
    throw 'For a published image use demo-published.ps1. To build locally, remove EX10_IMAGE from this shell first.'
}
& docker compose build python
if ($LASTEXITCODE -ne 0) { throw 'Image build failed. Check Docker Desktop and internet access.' }
& docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
if ($LASTEXITCODE -ne 0) { throw 'Could not start Exercise 10 containers.' }
& docker compose run --rm -T python init
if ($LASTEXITCODE -ne 0) { throw 'Exercise 10 replica set initialization failed.' }
