$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Experiment = 18
function Run {
    param([string]$Exe,[string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed ($LASTEXITCODE). Stop here and send the last error." }
}
function DC { param([string[]]$Arguments) Run docker (@('compose','-f','docker-compose.yml') + $Arguments) }
function Tool { param([string[]]$Arguments) DC (@('run','--rm','-T','runner') + $Arguments) }
function Ready {
    if (-not (Test-Path .env)) { throw 'Run SETUP.ps1 first.' }
    Run docker @('info','--format','{{.OSType}}')
}
function SaveJson {
    param([string]$Path,$Value)
    $json = $Value | ConvertTo-Json -Depth 50
    [IO.File]::WriteAllText((Join-Path $PWD $Path),$json,(New-Object Text.UTF8Encoding($false)))
}
