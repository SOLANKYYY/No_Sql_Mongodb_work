param([string]$Question='How can analysts reduce false positives?')
. "$PSScriptRoot/COMMON.ps1"
Ready
Tool @('ask','--question',$Question)
