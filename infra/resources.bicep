targetScope = 'resourceGroup'

@description('Base name for all resources')
param baseName string

@description('Azure region')
param location string

@description('API key for mobile app auth')
@secure()
param vitalisApiKey string

// ── Storage Account ───────────────────────────────────────────────

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${baseName}data'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'vitalis-data'
  properties: {
    publicAccess: 'None'
  }
}

// ── App Service Plan (Consumption) ────────────────────────────────

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'plan-${baseName}'
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true // Linux
  }
}

// ── Function App ──────────────────────────────────────────────────

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: 'func-${baseName}-api'
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      pythonVersion: '3.11'
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'VITALIS_API_KEY'
          value: vitalisApiKey
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: openai.properties.endpoint
        }
        {
          name: 'AZURE_OPENAI_KEY'
          value: openai.listKeys().key1
        }
        {
          name: 'AZURE_OPENAI_DEPLOYMENT'
          value: 'gpt-4o'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
    }
  }
}

// ── Azure OpenAI ──────────────────────────────────────────────────

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'oai-${baseName}'
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: 'oai-${baseName}'
    publicNetworkAccess: 'Enabled'
  }
}

resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 10 // 10K tokens per minute — minimal for single user
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────

output functionAppName string = functionApp.name
output storageAccountName string = storage.name
output openaiEndpoint string = openai.properties.endpoint
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}/api'
