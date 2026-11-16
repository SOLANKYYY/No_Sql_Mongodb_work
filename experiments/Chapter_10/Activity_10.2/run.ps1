$ErrorActionPreference = 'Stop'
$LabRunner = Join-Path (Split-Path $PSScriptRoot -Parent) 'RUN-ACTIVITY.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File $LabRunner -Activity inventory
if ($LASTEXITCODE -ne 0) { throw 'Activity failed.' }
