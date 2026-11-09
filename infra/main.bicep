// The Azure side of the explorer: one Foundry resource (Content Understanding lives in it) and the model
// deployments Content Understanding calls for field extraction. No keys: the signed-in user gets a data-plane role.

@description('Region. Content Understanding is only available in some regions; Sweden Central is one.')
param location string = resourceGroup().location

@description('Object id of the user who runs the app locally (az ad signed-in-user show --query id).')
param userObjectId string

@description('Chat models to deploy. The app uses the one named in COMPLETION_MODEL (extraction.py); the others are there to compare. Capacity is in thousands of tokens per minute.')
param chatModels array = [
  { name: 'gpt-6-luna', version: '2026-09-22', capacity: 200 }
  { name: 'gpt-6.1-sol', version: '2026-09-29', capacity: 200 }
]

var name = 'foundry-geert-cu-${uniqueString(resourceGroup().id)}'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

@batchSize(1) // deployments on one account must be created one at a time
resource chat 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [
  for model in chatModels: {
    parent: foundry
    name: model.name
    sku: { name: 'GlobalStandard', capacity: model.capacity }
    properties: {
      model: { format: 'OpenAI', name: model.name, version: model.version }
    }
  }
]

resource embedding 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundry
  name: 'text-embedding-3-large'
  dependsOn: [chat]
  sku: { name: 'GlobalStandard', capacity: 100 }
  properties: {
    model: { format: 'OpenAI', name: 'text-embedding-3-large', version: '1' }
  }
}

// "Cognitive Services User": call Content Understanding with an Entra token.
resource userRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundry
  name: guid(foundry.id, userObjectId, 'cognitive-services-user')
  properties: {
    principalId: userObjectId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'a97b65f3-24c7-4388-baec-2e87135dc908'
    )
  }
}

output endpoint string = 'https://${name}.services.ai.azure.com/'
