param([string]$DockerUser='solankyyy',[string]$StudentName='Solanki Om Narendra',[string]$RollNumber='24BTRCL190')
. "$PSScriptRoot/COMMON.ps1"
Ready
if($DockerUser -notmatch '^[a-z0-9][a-z0-9_-]+$') { throw 'Invalid Docker Hub username.' }
Tool @('validate')
SaveJson 'results/student.json' @{name=$StudentName;roll=$RollNumber}
Run docker @('login','--username',$DockerUser)
$repository="$DockerUser/nosql-exercise11"
$image="${repository}:exercise11"
Run docker @('build','-t',$image,'.')
Run docker @('push',$image)
Run docker @('pull',$image)
# Docker prints each digest on its own line; no JSON array conversion in PowerShell 5.1.
$lines = @(& docker image inspect $image --format '{{range .RepoDigests}}{{println .}}{{end}}')
if($LASTEXITCODE -ne 0) { throw 'Cannot inspect pulled image.' }
$digest = $null
foreach($line in $lines) {
    $candidate = ([string]$line).Trim()
    if($candidate -match ('^' + [regex]::Escape($repository) + '@sha256:[a-f0-9]{64}$')) { $digest=$candidate; break }
}
if(-not $digest) { throw 'No valid digest found. Image may be uploaded; do not rerun labs.' }
$url="https://hub.docker.com/r/$repository"
SaveJson 'results/published.json' @{image=$image;docker_url=$url;digest=[string]$digest;verified_pull=$true;timestamp=[DateTime]::UtcNow.ToString('o')}
$env:LAB_IMAGE=$image
Tool @('report')
Write-Host "EXERCISE 11 DOCKER LINK: $url"
Write-Host 'Check the repository is Public. Next: COLLECT.ps1.'
