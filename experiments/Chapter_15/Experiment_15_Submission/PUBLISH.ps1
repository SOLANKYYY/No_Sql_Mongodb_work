param([string]$DockerUser='solankyyy',[string]$StudentName='Solanki Om Narendra',[string]$RollNumber='24BTRCL190')
. "$PSScriptRoot/COMMON.ps1"
Ready
if($DockerUser -notmatch '^[a-z0-9][a-z0-9_-]+$') { throw 'Enter a valid lowercase Docker Hub username.' }
Tool @('validate')

foreach($log in @('metrics.log','scheduler.log','database-tools.jsonl')) {
    if(Test-Path (Join-Path 'logs' $log)) { Copy-Item (Join-Path 'logs' $log) (Join-Path 'results' $log) -Force }
}
SaveJson 'results/student.json' @{name=$StudentName;roll=$RollNumber}
Write-Host "Sign in to Docker Hub as $DockerUser using the browser instructions below. Never paste access tokens in chat."
# Run login directly: capturing its output can hide the interactive prompt.
& docker login
if($LASTEXITCODE -ne 0) { throw 'Docker login failed. Finish browser sign-in, then rerun PUBLISH.ps1.' }
$base='experiment15-runner:local'
Run docker @('build','-t',$base,'.')
$publications=@{}
foreach($n in @(15)) {
    $repository="$DockerUser/nosql-exercise$n"
    $image="${repository}:exercise$n"
    Run docker @('tag',$base,$image)
    Run docker @('push',$image)
    Run docker @('pull',$image)
    $digests=Run docker @('image','inspect',$image,'--format','{{json .RepoDigests}}') -Capture
    $prefix=$repository+'@sha256:'
    $digest=($digests | ConvertFrom-Json | Where-Object { $_.StartsWith($prefix) } | Select-Object -First 1)
    if(-not $digest) { throw "Could not verify Exercise $n digest." }
    $url="https://hub.docker.com/r/$repository"
    $entry=@{image=$image;docker_url=$url;digest=[string]$digest;verified_pull=$true;timestamp=[DateTime]::UtcNow.ToString('o')}
    $publications["$n"]=$entry
    SaveJson "results/published_$n.json" $entry
    Write-Host "EXERCISE $n DOCKER LINK: $url"
}
SaveJson 'results/published.json' @{experiments=$publications}
$env:LAB_IMAGE=$base
Tool @('report','--output','/results')
Write-Host 'Make the Exercise 15 repository Public. Submit results/Exercise_15_Final_Report.pdf.'
Write-Host 'Next: COLLECT.ps1.'
