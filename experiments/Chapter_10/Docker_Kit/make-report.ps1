param([Parameter(Mandatory=$true)][string]$DockerHubUsername)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if ($DockerHubUsername -notmatch '^[a-z0-9][a-z0-9_-]*$') { throw 'Enter your Docker Hub username only.' }
$LabHubUrl = "https://hub.docker.com/r/$DockerHubUsername/exercise10-transactions"
& docker compose run --rm -T python report --hub-url $LabHubUrl
if ($LASTEXITCODE -ne 0) { throw 'Report generation failed. Complete all experiments first.' }
Write-Host "Report generated with $LabHubUrl. Publication is checked separately by Docker push."
