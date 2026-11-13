param([switch]$AllowSystemDrive,[switch]$UsePublishedImage)
. "$PSScriptRoot/COMMON.ps1"
foreach($d in @('results','screenshots','.secrets')) { New-Item -ItemType Directory -Force $d | Out-Null }
if(-not (Test-Path '.secrets/root.env')) { New-Item -ItemType File '.secrets/root.env' | Out-Null }
Ready
if(-not $UsePublishedImage) { Run docker @('build','-t','experiment11-runner:local','.') }
Tool @('test')
DC @('up','-d','--wait','--wait-timeout','240','config','shard1','shard2')
Tool @('bootstrap')
DC @('up','-d','--wait','--wait-timeout','240','mongos')
Tool @('register')
Write-Host 'SETUP COMPLETE. Next: RUN.ps1. Use C: if preferred; no drive move is required.'
