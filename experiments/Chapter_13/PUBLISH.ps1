param([string]$DockerUser='solankyyy', [string]$StudentName='', [string]$RollNumber='')
. "$PSScriptRoot/COMMON.ps1"
Docker-Ready
if ($DockerUser -notmatch '^[a-z0-9][a-z0-9_-]+$') { throw 'Invalid Docker Hub username.' }
if (-not $StudentName) { $StudentName = Read-Host 'Enter your full student name for the report (not your Docker username)' }
while ($StudentName.Trim() -ieq $DockerUser) {
    Write-Host 'The report needs your student name; your Docker username remains unchanged.'
    $StudentName = Read-Host 'Enter your full student name'
}
if (-not $RollNumber) { $RollNumber = Read-Host 'Enter your roll/register number for the report' }
if (-not $StudentName.Trim() -or -not $RollNumber.Trim()) { throw 'Name and roll number are required.' }
$Image = "$DockerUser/mongodb-exercise13:exercise13"
$url = "https://hub.docker.com/r/$DockerUser/mongodb-exercise13"
Save-Json 'results/student.json' ([ordered]@{name=$StudentName;roll=$RollNumber})
# Validate evidence before building or publishing anything.
Run docker @('run','--rm','--entrypoint','python','--mount',"type=bind,source=$PSScriptRoot/results,target=/results",'exercise13-runner:local','/kit/scripts/report.py','--check-only','--results','/results')
# Keep interactive prompts attached to the terminal; Run captures stdout.
# Without --username, Docker Hub supports browser/device-code sign-in.
Write-Host "Docker Hub sign-in: use your $DockerUser account in the browser."
& docker login
if ($LASTEXITCODE -ne 0) { throw 'Docker Hub login failed. No image was published by this run.' }
Remove-Item results/published.json -ErrorAction SilentlyContinue
Remove-Item results/Exercise_13_Final_Report.pdf -ErrorAction SilentlyContinue
Run docker @('build','-t',$Image,'.')
Run docker @('push',$Image)
Run docker @('pull',$Image)
$digests = ((Run docker @('image','inspect','--format','{{json .RepoDigests}}',$Image) -Capture) -join "`n") | ConvertFrom-Json
$digest = @($digests | Where-Object { $_ -like "$DockerUser/mongodb-exercise13@sha256:*" })
if ($digest.Count -eq 0) { throw 'No repository digest found after push/pull; publication cannot be verified.' }
Save-Json 'results/published.json' ([ordered]@{image=$Image;docker_url=$url;digest=$digest[0];
    verified_pull=$true;timestamp=[DateTime]::UtcNow.ToString('o')})
Run docker @('run','--rm','--entrypoint','python','--mount',"type=bind,source=$PSScriptRoot/results,target=/results",$Image,'/kit/scripts/report.py','--results','/results')
Write-Host "PUBLISHED: $Image"
Write-Host "DOCKER URL: $url"
Write-Host 'Open the Docker Hub page, ensure the repository is Public, and capture the exercise13 tag (SCREENSHOT 06).'
Write-Host 'Submit results/Exercise_13_Final_Report.pdf to Classroom. Retain the image for demonstration.'
