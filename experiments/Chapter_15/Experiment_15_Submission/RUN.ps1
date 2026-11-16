. "$PSScriptRoot/COMMON.ps1"
Ready
DC @('up','-d','--wait','mongo')
Tool @('init')
DC @('up','-d','api')
Tool @('lab15')
Write-Host 'SCREENSHOT 15-1: tenant isolation/RBAC checks and concurrent rate-limit counts.'
Write-Host 'SCREENSHOT 15-2: five tenants with 100 tasks each, copy checksums and timing comparison.'
Write-Host 'Swagger API: http://localhost:8015/docs'
Write-Host 'Next: powershell -NoProfile -ExecutionPolicy Bypass -File .\PUBLISH.ps1'
