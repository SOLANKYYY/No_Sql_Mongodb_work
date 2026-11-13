. "$PSScriptRoot/COMMON.ps1"
if(-not (Test-Path 'results/Exercise_12_Final_Report.pdf')) { throw 'Run PUBLISH.ps1 or REPORT.ps1 successfully first.' }
$paths=@('scripts','tests','docs','results','screenshots','README.md','requirements.txt','Dockerfile','docker-compose.yml','.dockerignore','.gitignore','*.ps1')
Compress-Archive -Path $paths -DestinationPath 'Experiment_12_Completed_Submission.zip' -Force
Write-Host "Saved: $PSScriptRoot\Experiment_12_Completed_Submission.zip"
Write-Host 'Private .secrets, TLS keys, credentials and database volumes are excluded.'
