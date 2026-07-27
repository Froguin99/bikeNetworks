# Launch several run_all.py shard processes, each pinned to a different Overpass
# mirror (so they parallelise across independent servers without self-throttling).
#
#   Machine A:  .\run_shards.ps1 -Start 0 -Count 3 -N 6
#   Machine B:  .\run_shards.ps1 -Start 3 -Count 3 -N 6
#
# That is a 6-way split, 3 processes per machine, one per mirror. Add -DryRun to
# print the commands instead of launching. Stop any earlier run first, and keep the
# SAME -N on both machines (only -Start differs). Runs are resumable.
param(
    [int]$Start = 0,
    [int]$Count = 3,
    [int]$N = 6,
    [switch]$DryRun
)

$py = "C:\Users\b8008458\AppData\Local\miniforge3\envs\neatnetenv\python.exe"
$here = "C:\Users\b8008458\OneDrive - Newcastle University\2022 to 2023\PhD\bikeNetworksEDA\2026_edition\cycleform"
# Activate the env in each child window: without activation the env's Library\bin
# DLLs are off PATH and python dies with a SILENT hard crash (0xc06d007f delay-load
# failure) at the first native call -- seen at the Overpass fetch on machine B.
$hook = "C:\Users\b8008458\AppData\Local\miniforge3\shell\condabin\conda-hook.ps1"

# Each entry lists all mirrors (COMMA-SEPARATED, no quotes) with a DIFFERENT one
# first (its primary); with SHUFFLE off a process prefers its primary and only
# fails over to the rest. Comma-separated (not JSON) so it survives PowerShell
# quoting when passed to the child process.
$mirrors = @(
    'https://overpass-api.de/api,https://overpass.kumi.systems/api,https://overpass.private.coffee/api',
    'https://overpass.kumi.systems/api,https://overpass.private.coffee/api,https://overpass-api.de/api',
    'https://overpass.private.coffee/api,https://overpass-api.de/api,https://overpass.kumi.systems/api'
)

for ($k = 0; $k -lt $Count; $k++) {
    $i = $Start + $k
    $ep = $mirrors[$i % $mirrors.Count]
    $inner = "& '$hook'; conda activate neatnetenv; " +
             "`$env:CYCLEFORM_OVERPASS_SHUFFLE_ENDPOINTS='false'; " +
             "`$env:CYCLEFORM_OVERPASS_ENDPOINTS='$ep'; " +
             "Set-Location '$here'; " +
             "& '$py' run_all.py --shard $i/$N"
    if ($DryRun) {
        Write-Output "shard $i/$N ->"
        Write-Output "  $inner`n"
    } else {
        Start-Process powershell -ArgumentList '-NoExit', '-Command', $inner
        Write-Output "launched shard $i/$N (primary $($ep.Split(',')[0]))"
    }
}
