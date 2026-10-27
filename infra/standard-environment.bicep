param location string = 'francecentral'
param prefix string = 'pgdemo'
resource logs 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: '${prefix}-logs'
}
resource environment 'Microsoft.App/managedEnvironments@2026-07-01' = {
  name: '${prefix}-standard'
  location: location
  properties: {
    environmentMode: 'WorkloadProfiles'
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
  }
}
output environmentId string = environment.id
