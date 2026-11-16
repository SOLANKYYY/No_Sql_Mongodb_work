$ErrorActionPreference = 'Stop'
Get-Content (Join-Path $PSScriptRoot 'Evidence/faculty-results.txt')
