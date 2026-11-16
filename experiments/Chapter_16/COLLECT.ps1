. "$PSScriptRoot/COMMON.ps1"
$paths=@('results','scripts','tests','docs','screenshots','schemas','README.md','Dockerfile','requirements.txt','docker-compose.yml','*.ps1','.dockerignore','.gitignore')
Compress-Archive -Path $paths -DestinationPath Experiment_16_Completed_Submission.zip -Force
Write-Host 'Created Experiment_16_Completed_Submission.zip. Private .env, backups and logs are excluded.'
