. "$PSScriptRoot/COMMON.ps1"
Ready
DC @('up','-d','--wait','--wait-timeout','600','mongo')
Tool @('run')
Write-Host 'Save screenshots of RAG responses/history and the benchmark table/plot. Next: PUBLISH.ps1.'
