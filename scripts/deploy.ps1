param(
    [string]$SubscriptionId,
    [string]$ResourceGroup = 'rg-pitchguard-v2',
    [ValidateSet('francecentral','canadacentral','denmarkeast','belgiumcentral','norwayeast')]
    [string]$Location = 'francecentral',
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
if (!$Apply) {
    Write-Output 'Deployment plan: ACR Basic, Blob LRS, Log Analytics (0.1 GB/day cap), Application Insights, Consumption environment, web app (0-1 replicas), manual CPU job (no automatic retries).'
    Write-Output 'Uses existing Foundry model; does not create another Foundry account or delete any resource.'
    Write-Output 'Requires Azure CLI login, provider registration, resource deployment rights and RBAC assignment rights. See docs/RUNBOOK.md before -Apply.'
    exit 0
}
if (!$SubscriptionId) { throw 'Pass -SubscriptionId explicitly to select the authorized subscription.' }
if (!(Get-Command az -ErrorAction SilentlyContinue)) { throw 'Azure CLI is required; install it and run az login.' }
function Invoke-Azure {
    param([string[]]$Arguments)
    $result = & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Azure command failed; stopped without automatic deployment retries.' }
    return $result
}
$settings = @{}
foreach ($line in (Get-Content -LiteralPath '.env')) {
    if ($line -match '^\s*([A-Z_]+)\s*=(.*)$') { $settings[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'") }
}
if (!$settings['AZURE_OPENAI_API_KEY']) { throw 'Fill AZURE_OPENAI_API_KEY in .env first.' }
if (!(Test-Path -LiteralPath 'data/animation/runtime/S003/video.mp4')) { throw 'Rebuild runtime animation assets first.' }
Invoke-Azure -Arguments @('account','set','--subscription',$SubscriptionId) | Out-Null
Invoke-Azure -Arguments @('group','show','--name',$ResourceGroup,'--output','none') | Out-Null
$foundationText = Invoke-Azure -Arguments @('deployment','group','create','--name','pitchguard-foundation','--resource-group',$ResourceGroup,
    '--template-file','infra/foundation.bicep','--parameters',"location=$Location",'--query','properties.outputs','--output','json')
$foundation = ($foundationText -join "`n") | ConvertFrom-Json
$tag = 'demo-' + (Get-Date -Format 'yyyyMMddHHmmss')
$image = $foundation.registryServer.value + '/pitchguard:' + $tag
Invoke-Azure -Arguments @('acr','build','--registry',$foundation.registryName.value,'--image',"pitchguard:$tag",'.','--no-logs') | Out-Null
$randomBytes = New-Object byte[] 32
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$generator.GetBytes($randomBytes)
$generator.Dispose()
$analystToken = [Convert]::ToBase64String($randomBytes)
$params = @{}
foreach ($name in @('registryServer','environmentId','storageUrl','apiIdentityId','apiClientId','apiPrincipalId',
    'workerIdentityId','workerClientId','insightsConnection')) { $params[$name] = @{value=$foundation.$name.value} }
$params['location'] = @{value=$Location}
$params['image'] = @{value=$image}
$params['modelEndpoint'] = @{value=$settings['AZURE_OPENAI_ENDPOINT']}
$params['modelDeployment'] = @{value=$settings['AZURE_OPENAI_DEPLOYMENT']}
$params['modelKey'] = @{value=$settings['AZURE_OPENAI_API_KEY']}
$params['analystToken'] = @{value=$analystToken}
New-Item -ItemType Directory -Force -Path '.state' | Out-Null
$parameterPath = Join-Path $projectRoot '.state/deploy.parameters.json'
$parameterDocument = @{'$schema'='https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#';contentVersion='1.0.0.0';parameters=$params}
$parameterDocument | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $parameterPath -Encoding utf8
try {
    $result = Invoke-Azure -Arguments @('deployment','group','create','--name','pitchguard-runtime','--resource-group',$ResourceGroup,
        '--template-file','infra/runtime.bicep','--parameters',"@$parameterPath",'--query','properties.outputs','--output','json')
    Write-Output ($result -join "`n")
    $analystToken | Set-Content -LiteralPath '.state/analyst-token.txt' -Encoding utf8
    Write-Output 'Analyst access token saved locally to .state/analyst-token.txt (Git-ignored); not printed.'
} finally {
    Remove-Item -LiteralPath $parameterPath -Force
}
