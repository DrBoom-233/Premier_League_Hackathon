param(
    [ValidateSet('all', 'S001', 'S002', 'S003', 'R001')][string]$Scenario = 'all',
    [string]$Blender = '',
    [switch]$Preview,
    [switch]$Stills,
    [switch]$Overwrite
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $Blender) { $Blender = Join-Path $projectRoot '.tools\blender-4.5.9-windows-x64\blender.exe' }
if (-not (Test-Path -LiteralPath $Blender)) { throw 'Blender not found. Run setup_blender.py or pass -Blender C:\path\blender.exe.' }
$oldResources = $env:BLENDER_USER_RESOURCES
try {
    $env:BLENDER_USER_RESOURCES = Join-Path $projectRoot '.tools\blender-user'
    $clips = if ($Scenario -eq 'all') { @('S001', 'S002', 'S003', 'R001') } else { @($Scenario) }
    foreach ($clipId in $clips) {
        $options = @('-b', '-t', '8', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'build_scene.py'), '--',
            '--config', (Join-Path $projectRoot "data\animation\configs\$clipId.json"),
            '--output', (Join-Path $projectRoot 'data\animation'))
        if ($Preview) { $options += '--preview' }
        if ($Stills) { $options += '--stills' }
        if ($Overwrite) { $options += '--overwrite' }
        & $Blender @options
        if ($LASTEXITCODE -ne 0) { throw "Blender failed for $clipId (exit $LASTEXITCODE)" }
    }
} finally {
    $env:BLENDER_USER_RESOURCES = $oldResources
}
