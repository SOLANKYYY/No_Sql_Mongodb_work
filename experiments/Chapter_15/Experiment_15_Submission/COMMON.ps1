$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Run {
    param([string]$Exe,[string[]]$Arguments,[switch]$Capture)
    if ($Capture) {
        $value = & $Exe @Arguments
        if ($LASTEXITCODE -ne 0) { throw "$Exe failed ($LASTEXITCODE). Stop and send the error text." }
        return $value
    }
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed ($LASTEXITCODE). Stop and send the error text." }
}
function DC { param([string[]]$Arguments) Run docker (@('compose','-f','docker-compose.yml') + $Arguments) }
function Tool { param([string[]]$Arguments) DC (@('run','--rm','-T','runner') + $Arguments) }
function Ready {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Open Docker Desktop and reopen PowerShell.' }
    $kind=Run docker @('info','--format','{{.OSType}}') -Capture
    if ($kind -ne 'linux') { throw 'Docker Desktop must be running in Linux containers mode.' }
    if (-not (Test-Path .env)) { throw 'Run SETUP.ps1 first.' }
}
function SaveJson { param([string]$Path,$Value) $Value | ConvertTo-Json -Depth 50 | Set-Content -Encoding UTF8 $Path }
