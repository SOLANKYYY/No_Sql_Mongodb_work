. "$PSScriptRoot/COMMON.ps1"
if(-not (Test-Path 'results/Exercise_18_Final_Report.pdf')) { throw 'Generate the final report first.' }
$paths=@('data/threats.jsonl','data/source.json','data/README.md','scripts','tests','docs','results','screenshots','README.md','requirements.txt','Dockerfile','docker-compose.yml','*.ps1')
Compress-Archive -Path $paths -DestinationPath 'Experiment_18_Completed_Submission.zip' -Force
Write-Host 'Created completed submission ZIP. Public lab input is included; model cache and .env are excluded.'
