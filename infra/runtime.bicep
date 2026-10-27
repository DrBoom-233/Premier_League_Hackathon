param location string = 'francecentral'
param prefix string = 'pitchguard'
param image string
param registryServer string
param environmentId string
param storageUrl string
param apiIdentityId string
param apiClientId string
param apiPrincipalId string
param workerIdentityId string
param workerClientId string
param insightsConnection string
param modelEndpoint string
param modelDeployment string = 'gpt-4.1-mini'
@secure()
param modelKey string
@secure()
param analystToken string
@secure()
param analysisCodes string
var commonEnv = [
  { name: 'PITCHGUARD_LOCAL_ONLY', value: 'false' }
  { name: 'PITCHGUARD_STORAGE_ACCOUNT_URL', value: storageUrl }
  { name: 'AZURE_OPENAI_ENDPOINT', value: modelEndpoint }
  { name: 'AZURE_OPENAI_DEPLOYMENT', value: modelDeployment }
  { name: 'AZURE_OPENAI_API_VERSION', value: '2024-10-21' }
  { name: 'AZURE_OPENAI_API_KEY', secretRef: 'model-key' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insightsConnection }
]
resource job 'Microsoft.App/jobs@2024-03-01' = {
  name: '${prefix}-worker'
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${workerIdentityId}': {} } }
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 300
      replicaRetryLimit: 0
      manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
      secrets: [{ name: 'model-key', value: modelKey }]
      registries: [{ server: registryServer, identity: workerIdentityId }]
    }
    template: {
      containers: [{
        name: 'worker'
        image: image
        command: ['python', '-m', 'src.backend.cloud']
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: concat(commonEnv, [{ name: 'AZURE_CLIENT_ID', value: workerClientId }])
      }]
    }
  }
}
resource starterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, prefix, 'start-finite-job')
  properties: {
    roleName: '${prefix} finite job starter'
    description: 'Read and start only; no wildcard/listSecrets permission.'
    type: 'CustomRole'
    assignableScopes: [resourceGroup().id]
    permissions: [{ actions: ['Microsoft.App/jobs/read', 'Microsoft.App/jobs/start/action'], notActions: [], dataActions: [], notDataActions: [] }]
  }
}
resource startPermission 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(job.id, apiIdentityId, 'start')
  scope: job
  properties: { principalId: apiPrincipalId, principalType: 'ServicePrincipal', roleDefinitionId: starterRole.id }
}
resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-web'
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${apiIdentityId}': {} } }
  properties: {
    managedEnvironmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: 8000, transport: 'auto', allowInsecure: false }
      registries: [{ server: registryServer, identity: apiIdentityId }]
      secrets: [{ name: 'model-key', value: modelKey }, { name: 'analyst-token', value: analystToken }, { name: 'analysis-codes', value: analysisCodes }]
    }
    template: {
      containers: [{
        name: 'web'
        image: image
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: concat(commonEnv, [
          { name: 'AZURE_CLIENT_ID', value: apiClientId }
          { name: 'PITCHGUARD_JOB_RESOURCE_ID', value: job.id }
          { name: 'PITCHGUARD_ANALYST_TOKEN', secretRef: 'analyst-token' }
          { name: 'PITCHGUARD_ANALYSIS_CODES', secretRef: 'analysis-codes' }
        ]) }]
      scale: { minReplicas: 1, maxReplicas: 1, rules: [{ name: 'http', http: { metadata: { concurrentRequests: '10' } } }] }
    }
  }
  dependsOn: [startPermission]
}
output demoUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
output jobId string = job.id
