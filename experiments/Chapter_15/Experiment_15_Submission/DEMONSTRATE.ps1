param([string]$Image='solankyyy/nosql-exercise15:exercise15')
. "$PSScriptRoot/COMMON.ps1"
Ready
Run docker @('pull',$Image)
$destination=Join-Path $PSScriptRoot ('demonstration-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory $destination | Out-Null
Run docker @('run','--rm','--mount',"type=bind,source=$destination,target=/work",$Image,'export')
Copy-Item .env (Join-Path $destination '.env')
$env:LAB_IMAGE=$Image
& (Join-Path $destination 'SETUP.ps1') -UsePublishedImage -Image $Image
& (Join-Path $destination 'RUN.ps1')
Write-Host 'Demonstration finished using the published image. Fresh evidence is in the demonstration folder/results.'
