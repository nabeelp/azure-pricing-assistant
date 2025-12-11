targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g., dev, test, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Deployment timestamp for unique resource naming')
param timestamp string = utcNow('yyyyMMddHHmmss')

@description('Azure AI Foundry Project Endpoint')
@secure()
param azureAiProjectEndpoint string = ''

@description('SKU for the App Service Plan')
@allowed([
  'B1'
  'B2'
  'B3'
  'S1'
  'S2'
  'S3'
  'P1v2'
  'P2v2'
  'P3v2'
])
param appServicePlanSku string = 'B1'

// Generate globally unique resource names
var resourceToken = uniqueString(subscription().id, environmentName, location)
var tags = {
  'azd-env-name': environmentName
  application: 'azure-pricing-assistant'
}

// Create resource group for all resources
resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}-${resourceToken}'
  location: location
  tags: tags
}

// Deploy main application infrastructure
module appResources './resources.bicep' = {
  name: 'app-resources-${timestamp}'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    appServicePlanSku: appServicePlanSku
    azureAiProjectEndpoint: azureAiProjectEndpoint
    tags: tags
  }
}

// Outputs for azd and deployment reference
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_APP_SERVICE_NAME string = appResources.outputs.appServiceName
output AZURE_APP_SERVICE_URL string = appResources.outputs.appServiceUrl
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appResources.outputs.applicationInsightsConnectionString
