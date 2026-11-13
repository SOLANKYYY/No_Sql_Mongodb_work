. "$PSScriptRoot/COMMON.ps1"
DC @('stop')
Write-Host 'Containers stopped. Volumes and evidence preserved.'
