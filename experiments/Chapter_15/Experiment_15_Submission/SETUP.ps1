param([switch]$AllowSystemDrive,[switch]$UsePublishedImage,[string]$Image='solankyyy/nosql-exercise15:exercise15')
. "$PSScriptRoot/COMMON.ps1"
$projectDrive=[IO.Path]::GetPathRoot($PSScriptRoot)
if ($projectDrive.TrimEnd('\') -eq $env:SystemDrive -and -not $AllowSystemDrive) {
    throw 'Extract this kit onto E: (or another drive) first. See docs/E_DRIVE_SETUP.md. Moving the project does not move Docker disk storage.'
}
foreach($folder in @('results','logs','backups','screenshots')) { New-Item -ItemType Directory -Force $folder | Out-Null }
if (-not (Test-Path .env)) {
    $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $bytes=New-Object byte[] 32; $rng.GetBytes($bytes); $jwt=([BitConverter]::ToString($bytes)).Replace('-','').ToLower()
        $rng.GetBytes($bytes); $password=([BitConverter]::ToString($bytes)).Replace('-','').ToLower()
        @("JWT_SECRET=$jwt","DEMO_PASSWORD=$password",'WEBHOOK_URL=') | Set-Content -Encoding ASCII .env
    } finally { $rng.Dispose() }
}
Ready
Write-Host 'Project backups, logs and results are stored at:' $PSScriptRoot
Write-Host 'MongoDB/Cassandra/Neo4j volumes remain inside Docker disk storage. Move that disk to E: in Docker Desktop Settings before building.'
if($UsePublishedImage) { $env:LAB_IMAGE=$Image; Run docker @('pull',$Image) }
else { $env:LAB_IMAGE='experiment15-runner:local'; Run docker @('build','-t',$env:LAB_IMAGE,'.') }
Tool @('unit-tests')
DC @('up','-d','--wait','mongo')
Tool @('init')
Write-Host 'SETUP COMPLETE. Next: powershell -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1'
