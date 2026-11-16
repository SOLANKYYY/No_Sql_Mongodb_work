$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Compose = 'docker-compose-production.yml'
function Run {
    param([string]$Exe, [string[]]$Arguments, [switch]$Capture)
    $out = & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE. Stop here and send the error text." }
    if ($Capture) { return $out } else { $out | ForEach-Object { Write-Host $_ } }
}
function Docker-Ready {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install Docker Desktop, then reopen PowerShell.' }
    & docker info --format '{{.OSType}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and wait until its Linux engine is running.' }
    $osType = Run docker @('info','--format','{{.OSType}}') -Capture
    if ($osType -ne 'linux') { throw 'Switch Docker Desktop to Linux containers.' }
    Run docker @('compose','version')
}
function Set-LabImage {
    param([string]$Image)
    $env:LAB_IMAGE = $Image
}
function Save-Json {
    param([string]$Path, $Value)
    $Value | ConvertTo-Json -Depth 30 | Set-Content -Encoding UTF8 $Path
}
