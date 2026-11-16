param([switch]$AllowSystemDrive,[switch]$UsePublishedImage)
. "$PSScriptRoot/COMMON.ps1"
foreach($d in @('results','screenshots','data','.cache')) { New-Item -ItemType Directory -Force $d | Out-Null }
if(-not (Test-Path .env)) {
    @'
STUDENT_NAME=Solanki Om Narendra
ROLL_NUMBER=24BTRCL190
MONGO_URI=mongodb://mongo:27017/?directConnection=true
THREAT_API_URL=
THREAT_API_TOKEN=
'@ | Set-Content .env -Encoding ASCII
}
Ready
Write-Host 'Using this project folder. Docker images and volumes use Docker Desktop disk storage.'
Run docker @('system','df')
if(-not $UsePublishedImage) { Run docker @('build','-t','experiment18-runner:local','.') }
Tool @('test')
Write-Host 'SETUP COMPLETE. Next: RUN.ps1. Stop other lab containers first to free RAM.'
