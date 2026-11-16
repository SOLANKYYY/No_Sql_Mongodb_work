param([string]$Image='solankyyy/mongodb-exercise13:exercise13')
. "$PSScriptRoot/COMMON.ps1"
Docker-Ready
$destination = Join-Path $PSScriptRoot ('demonstration-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $destination | Out-Null
Run docker @('pull',$Image)
Run docker @('run','--rm','--mount',"type=bind,source=$destination,target=/work",$Image,'export')
if ((Test-Path .env) -and (Test-Path .secrets/keyfile)) {
    Copy-Item .env (Join-Path $destination '.env')
    New-Item -ItemType Directory -Path (Join-Path $destination '.secrets') | Out-Null
    Copy-Item .secrets/keyfile (Join-Path $destination '.secrets/keyfile')
}
Write-Host "Kit extracted from published image to $destination"
Write-Host 'The following runs the published code and creates fresh test evidence.'
& (Join-Path $destination 'START.ps1') -UsePublishedImage -Image $Image
if (-not $?) { throw 'Published-image Compose demonstration failed.' }
& (Join-Path $destination 'LAB13_2.ps1') -Image $Image
if (-not $?) { throw 'Published-image Kubernetes demonstration failed.' }
Write-Host 'Demonstration completed using the published image. Fresh evidence is in the demonstration folder/results.'
