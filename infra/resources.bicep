@description('Primary location for all resources')
param location string

@description('Name of the environment')
param environmentName string

@description('Unique token for resource naming')
param resourceToken string

@description('SKU for the App Service Plan')
param appServicePlanSku string

@description('Azure AI Foundry Project Endpoint')
@secure()
param azureAiProjectEndpoint string

@description('Resource tags')
param tags object

// Application Insights for monitoring and observability
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${environmentName}-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${environmentName}-${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// App Service Plan for hosting the web application
resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'asp-${environmentName}-${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: appServicePlanSku
  }
  kind: 'linux'
  properties: {
    reserved: true // Required for Linux
  }
}

// App Service for the web application
resource appService 'Microsoft.Web/sites@2023-12-01' = {
  name: 'app-${environmentName}-${resourceToken}'
  location: location
  tags: union(tags, {
    'azd-service-name': 'web'
  })
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: appServicePlanSku != 'B1'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      appSettings: [
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
        {
          name: 'AZURE_AI_PROJECT_ENDPOINT'
          value: azureAiProjectEndpoint
        }
        {
          name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME'
          value: 'gpt-4o-mini'
        }
        {
          name: 'APPLICATIONINSIGHTS_LIVE_METRICS'
          value: 'false'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
        {
          name: 'PORT'
          value: '8000'
        }
      ]
      pythonVersion: '3.11'
      appCommandLine: 'gunicorn --bind=0.0.0.0:8000 --workers=4 --threads=2 --timeout=120 --access-logfile=- --error-logfile=- app:app'
    }
  }
}

// Outputs
output appServiceName string = appService.name
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output appServicePrincipalId string = appService.identity.principalId
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
