param([string]$DockerUser='solankyyy')
. "$PSScriptRoot/COMMON.ps1"
$env:LAB_IMAGE="$DockerUser/nosql-exercise11:exercise11"
Run docker @('pull',$env:LAB_IMAGE)
& "$PSScriptRoot/SETUP.ps1" -UsePublishedImage -AllowSystemDrive
if(-not $?) { throw 'Setup failed.' }
& "$PSScriptRoot/RUN.ps1"
