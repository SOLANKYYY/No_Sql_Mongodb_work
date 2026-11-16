. "$PSScriptRoot/COMMON.ps1"
Ready
DC @('stop','scheduler','monitor')
DC @('up','-d','--wait','mongo')
Tool @('init')
Write-Host 'Lab 14.1 takes about one minute: three LIVE measurements at 30-second intervals.'
Tool @('monitor','--samples','3','--interval','30')
Write-Host 'SCREENSHOT 14-1: metrics and sample_count=3 / passed=true.'
Tool @('alert-test')
Write-Host 'SCREENSHOT 14-2: labelled threshold fixtures and successful local HTTP webhook delivery.'
DC @('up','-d','--wait','mongo-restore')
Tool @('lab14')
Write-Host 'SCREENSHOT 14-3: restore/PITR results and 1,000 / 10,000 / 100,000 timing rows.'
Remove-Item results/scheduler_status.json -ErrorAction SilentlyContinue
DC @('up','-d','scheduler')
Tool @('wait-scheduler')
DC @('stop','mongo-restore')
Write-Host 'Exercise 14 complete. Scheduler remains running hourly while Docker/Desktop and the computer stay awake.'
Write-Host 'Next: powershell -NoProfile -ExecutionPolicy Bypass -File .\PUBLISH.ps1'
