. "$PSScriptRoot/COMMON.ps1"
Ready
# Validate the supplied data before starting the heavy databases.
Tool @('prepare')
DC @('up','-d','--wait','--wait-timeout','900','mongo','cassandra','neo4j')
Tool @('run')
Write-Host 'Save screenshots of data validation, the benchmark table and graph review. Next: PUBLISH.ps1.'
