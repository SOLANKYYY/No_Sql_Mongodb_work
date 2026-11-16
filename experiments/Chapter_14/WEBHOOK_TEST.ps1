. "$PSScriptRoot/COMMON.ps1"
Ready
Write-Host 'This explicitly sends a labelled TEST alert to the private WEBHOOK_URL configured in .env.'
Tool @('alert-test','--external')
