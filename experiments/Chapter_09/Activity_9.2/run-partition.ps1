# Run the complete controller from the shared Docker kit.
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '..\Docker_Kit\run-partition.ps1')
