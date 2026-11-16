. "$PSScriptRoot/COMMON.ps1"
Get-PSDrive -PSProvider FileSystem | Select-Object Name,Root,@{Name='UsedGB';Expression={[Math]::Round($_.Used/1GB,2)}},@{Name='FreeGB';Expression={[Math]::Round($_.Free/1GB,2)}} | Format-Table -AutoSize
Write-Host 'Project path:' $PSScriptRoot
Write-Host 'Check Docker Desktop > Settings > Resources > Advanced for the actual Docker disk image location.'
if(Get-Command docker -ErrorAction SilentlyContinue) { & docker system df }
