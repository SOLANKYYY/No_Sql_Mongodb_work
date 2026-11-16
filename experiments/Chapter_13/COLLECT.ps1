. "$PSScriptRoot/COMMON.ps1"
if (-not (Test-Path results)) { throw 'Run the labs first.' }
Compress-Archive -Path results -DestinationPath Exercise_13_Results.zip -Force
Write-Host 'Send Exercise_13_Results.zip and the screenshots to this chat. Never send .env or .secrets.'
