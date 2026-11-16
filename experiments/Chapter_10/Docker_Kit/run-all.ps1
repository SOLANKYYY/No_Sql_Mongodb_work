param([string]$HubUrl = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& powershell -NoProfile -ExecutionPolicy Bypass -File ./start.ps1
if ($LASTEXITCODE -ne 0) { throw 'Setup failed.' }
$LabRunArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', './run-experiments.ps1')
if ($HubUrl) { $LabRunArgs += @('-HubUrl', $HubUrl) }
& powershell @LabRunArgs
if ($LASTEXITCODE -ne 0) { throw 'Experiment run did not complete. Read the error above.' }
