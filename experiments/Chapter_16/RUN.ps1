. "$PSScriptRoot/COMMON.ps1"
Ready
DC @('up','-d','--wait','mongo')
Tool @('init')
Write-Host 'Starting Cassandra and Neo4j. First start may take several minutes; wait for both to become healthy.'
DC @('up','-d','--wait','--wait-timeout','720','cassandra','neo4j')
Tool @('unit-tests')
Tool @('lab16')
Write-Host 'SCREENSHOT 16-1: equal enrollment-query results across three LIVE databases.'
Write-Host 'SCREENSHOT 16-2: merged fraud analysis, latencies and tests passed.'
Write-Host 'Neo4j Browser: http://localhost:7474 (connect without authentication to bolt://localhost:7687).'
Write-Host 'All experiments done. Next: powershell -NoProfile -ExecutionPolicy Bypass -File .\PUBLISH.ps1'
