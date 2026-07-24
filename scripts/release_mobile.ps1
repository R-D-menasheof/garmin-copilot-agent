param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [int]$BuildNumber,

    [Parameter(Mandatory = $true)]
    [string]$Notes,

    [switch]$SkipTests,
    [switch]$SkipUpload
)

$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'release_mobile.py'
$arguments = @(
    $scriptPath,
    '--version', $Version,
    '--build-number', $BuildNumber,
    '--notes', $Notes
)

if ($SkipTests) {
    $arguments += '--skip-tests'
}
if ($SkipUpload) {
    $arguments += '--skip-upload'
}

& python @arguments
exit $LASTEXITCODE