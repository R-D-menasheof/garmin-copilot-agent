targetScope = 'subscription'

@description('Base name for all resources')
param baseName string = 'vitalis'

@description('Azure region for resources')
param location string = 'swedencentral'

@description('API key for the Vitalis mobile app')
@secure()
param vitalisApiKey string

// ── Resource Group ────────────────────────────────────────────────

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${baseName}'
  location: location
}

// ── Deploy all resources into the resource group ──────────────────

module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    baseName: baseName
    location: location
    vitalisApiKey: vitalisApiKey
  }
}

// ── Outputs ───────────────────────────────────────────────────────

output RESOURCE_GROUP string = rg.name
output FUNCTION_APP_NAME string = resources.outputs.functionAppName
output STORAGE_ACCOUNT_NAME string = resources.outputs.storageAccountName
output OPENAI_ENDPOINT string = resources.outputs.openaiEndpoint
output FUNCTION_APP_URL string = resources.outputs.functionAppUrl
