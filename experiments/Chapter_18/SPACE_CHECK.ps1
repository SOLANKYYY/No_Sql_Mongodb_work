. "$PSScriptRoot/COMMON.ps1"
Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free
Run docker @('system','df')
