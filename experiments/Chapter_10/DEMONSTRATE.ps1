$ErrorActionPreference = 'Stop'
$LabDemoScript = Join-Path $PSScriptRoot 'Docker_Kit/demo-published.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File $LabDemoScript -Image 'solankyyy/exercise10-transactions@sha256:a7cb4c956e7fd866ecdbedd534699a3cdbace4d472b8ffa33fe273b72e0c5e2e'
if ($LASTEXITCODE -ne 0) { throw 'Exercise 10 demonstration failed; inspect the preceding error.' }
