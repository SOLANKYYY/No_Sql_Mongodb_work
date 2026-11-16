. "$PSScriptRoot/COMMON.ps1"
if(-not (Test-Path 'results/Exercise_17_Final_Report.pdf')) { throw 'Generate the final report first.' }
$paths=@('data','scripts','tests','docs','results','screenshots','README.md','requirements.txt','Dockerfile','docker-compose.yml','*.ps1')
Compress-Archive -Path $paths -DestinationPath 'Experiment_17_Completed_Submission.zip' -Force
Write-Host 'Created completed submission ZIP. Raw exports, model cache and .env are excluded.'
