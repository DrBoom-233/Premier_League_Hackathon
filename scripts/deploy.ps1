param([string]$SubscriptionId, [switch]$Apply)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$releaseRoot = Split-Path $projectRoot -Parent
Set-Location $projectRoot
if (!$Apply) {
    Write-Output 'Isolated update: local Docker build/push, existing Basic registry, one small HTTPS web replica, finite analysis Job, private Blob state and persistent 10-use judge codes.'
    Write-Output 'Target: Azure for Students / rg-pitchguard-demo-20261026. Existing Foundry and local fallback are excluded. No ACR Tasks or resource deletions.'
    exit 0
}
if (!$SubscriptionId) { throw 'Pass the intended subscription ID explicitly.' }
$resourceGroup = 'rg-pitchguard-demo-20261026'
$azureCli = Join-Path $releaseRoot 'tools/azure-cli/bin/az.cmd'
$env:AZURE_CONFIG_DIR = Join-Path $releaseRoot 'azure-config'
$env:AZURE_CORE_COLLECT_TELEMETRY = 'false'
$pythonPath = Join-Path $releaseRoot 'local-fallback/.venv/Scripts/python.exe'
$originalRoot = Split-Path (Split-Path (Split-Path $releaseRoot -Parent) -Parent) -Parent
$bicepPath = Join-Path $originalRoot '.tools/bicep.exe'
function Invoke-Azure {
    param([string[]]$Arguments)
    $result = & $azureCli @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Azure command failed; no automatic deployment retry.' }
    return $result
}
$isolation = Invoke-Azure -Arguments @('group','show','--subscription',$SubscriptionId,'--name',$resourceGroup,'--query','tags.isolation','-o','tsv')
if ($isolation -ne 'azure-demo-local-preserved') { throw 'Target group is not marked as this isolated demo.' }
$foundation = Get-Content (Join-Path $releaseRoot 'foundation.outputs.json') -Raw | ConvertFrom-Json
$tag = 'demo-' + (Get-Date -Format 'yyyyMMddHHmmss')
$image = $foundation.registryServer.value + '/pitchguard:' + $tag
& docker build --tag $image .
if ($LASTEXITCODE -ne 0) { throw 'Image build failed; hosted revision unchanged.' }
$dockerConfig = Join-Path $releaseRoot 'docker-config'
New-Item -ItemType Directory -Force -Path $dockerConfig | Out-Null
$registryToken = Invoke-Azure -Arguments @('acr','login','--subscription',$SubscriptionId,'--name',$foundation.registryName.value,'--expose-token','--query','accessToken','-o','tsv')
$registryToken | docker --config $dockerConfig login $foundation.registryServer.value --username 00000000-0000-0000-0000-000000000000 --password-stdin
if ($LASTEXITCODE -ne 0) { throw 'Registry login failed.' }
& docker --config $dockerConfig push $image
if ($LASTEXITCODE -ne 0) { throw 'Image push failed; hosted revision unchanged.' }
& $pythonPath scripts/prepare_runtime_parameters.py $tag
if ($LASTEXITCODE -ne 0) { throw 'Private parameter preparation failed.' }
$template = Join-Path $releaseRoot 'runtime.validated.json'
& $bicepPath build infra/runtime.bicep --outfile $template
if ($LASTEXITCODE -ne 0) { throw 'Runtime template compilation failed.' }
$parameterPath = Join-Path $projectRoot '.state/runtime.parameters.json'
try {
    Invoke-Azure -Arguments @('deployment','group','what-if','--subscription',$SubscriptionId,'--resource-group',$resourceGroup,
        '--template-file',$template,'--parameters',"@$parameterPath",'--no-pretty-print','-o','json') |
        Set-Content (Join-Path $releaseRoot 'runtime.what-if.json') -Encoding utf8
    $preview = Get-Content (Join-Path $releaseRoot 'runtime.what-if.json') -Raw | ConvertFrom-Json
    $scope = "/subscriptions/$SubscriptionId/resourceGroups/$resourceGroup/"
    foreach ($change in $preview.changes) {
        if ($change.changeType -eq 'Delete' -or !$change.resourceId.StartsWith($scope,[System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'Unexpected deletion or scope in deployment preview.'
        }
    }
    Invoke-Azure -Arguments @('deployment','group','create','--subscription',$SubscriptionId,'--resource-group',$resourceGroup,
        '--name','pitchguard-runtime','--template-file',$template,'--parameters',"@$parameterPath",'--query','properties.outputs','-o','json') |
        Set-Content (Join-Path $releaseRoot 'runtime.outputs.json') -Encoding utf8
    Write-Output 'Isolated update completed. URL: ../runtime.outputs.json. Existing judge codes were retained.'
} finally {
    if (Test-Path -LiteralPath $parameterPath) { Remove-Item -LiteralPath $parameterPath -Force }
}
