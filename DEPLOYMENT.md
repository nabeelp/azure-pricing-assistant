# Azure Deployment Guide

This guide walks you through deploying the Azure Pricing Assistant to Azure App Service using Azure Developer CLI (azd).

## Prerequisites

1. **Install Azure Developer CLI**
   - macOS: `brew install azd`
   - Windows: `winget install microsoft.azd`
   - Linux: `curl -fsSL https://aka.ms/install-azd.sh | bash`
   - [All installation options](https://aka.ms/install-azd)

2. **Install Azure CLI**
   - macOS: `brew install azure-cli`
   - Windows: `winget install microsoft.azurecli`
   - [All installation options](https://docs.microsoft.com/cli/azure/install-azure-cli)

3. **Azure Subscription**
   - An active Azure subscription with permissions to create resources
   - Contributor role or higher on the subscription

4. **Azure AI Foundry Project**
   - An existing Azure AI Foundry project with a deployed model
   - Note the project endpoint URL (format: `https://<project-name>.api.azureml.ms`)

## Deployment Steps

### Step 1: Authentication

Login to Azure:

```bash
# Login with Azure Developer CLI
azd auth login

# Login with Azure CLI
az login

# (Optional) Set your subscription
az account set --subscription <subscription-id>
```

### Step 2: Initialize Environment

Create a new azd environment:

```bash
# Create new environment (e.g., 'dev', 'test', 'prod')
azd env new <environment-name>

# Example:
azd env new dev
```

### Step 3: Configure Environment Variables

Set required configuration:

```bash
# Required: Set your Azure AI Foundry endpoint
azd env set AZURE_AI_PROJECT_ENDPOINT "<your-ai-foundry-endpoint>"

# Example:
azd env set AZURE_AI_PROJECT_ENDPOINT "https://myproject.api.azureml.ms"
```

Optional configurations:

```bash
# Change App Service Plan SKU (default: B1)
# Options: B1, B2, B3, S1, S2, S3, P1v2, P2v2, P3v2
azd env set APP_SERVICE_PLAN_SKU "S1"

# Set Azure location (default: uses azd default)
azd env set AZURE_LOCATION "eastus"

# Set Flask secret key (auto-generated if not set)
azd env set FLASK_SECRET_KEY "$(openssl rand -hex 32)"
```

### Step 4: Preview Deployment

Before deploying, preview what resources will be created:

```bash
azd provision --preview
```

Review the output to ensure:
- Resource Group name is correct
- Location is appropriate
- App Service Plan SKU is suitable
- All expected resources are listed

### Step 5: Deploy

Deploy infrastructure and application:

```bash
# Deploy everything (infrastructure + code)
azd up
```

This command will:
1. Create a resource group
2. Deploy Bicep templates (App Service Plan, App Service, Application Insights, Log Analytics)
3. Configure App Service with managed identity
4. Build and deploy the Python application
5. Set environment variables and app settings

Deployment typically takes 5-10 minutes.

### Step 6: Verify Deployment

After deployment completes, you'll see output like:

```
SUCCESS: Your application was provisioned and deployed to Azure in 8 minutes 32 seconds.

You can view the resources created under the resource group rg-dev-abc123 in Azure Portal:
https://portal.azure.com/#@/resource/subscriptions/.../resourceGroups/rg-dev-abc123

Find more details in the output variables:
  AZURE_LOCATION: eastus
  AZURE_RESOURCE_GROUP: rg-dev-abc123
  AZURE_APP_SERVICE_NAME: app-dev-abc123
  AZURE_APP_SERVICE_URL: https://app-dev-abc123.azurewebsites.net
```

Visit the `AZURE_APP_SERVICE_URL` to access your deployed application.

## Post-Deployment Configuration

### Configure Managed Identity Permissions

The App Service uses a System-Assigned Managed Identity to authenticate with Azure AI Foundry. You need to grant it appropriate permissions:

1. Get the App Service Principal ID:
   ```bash
   az webapp identity show --name <app-service-name> --resource-group <resource-group-name> --query principalId -o tsv
   ```

2. Grant permissions to Azure AI Foundry:
   ```bash
   # Reader role on the AI project
   az role assignment create \
     --assignee <principal-id> \
     --role "Reader" \
     --scope "/subscriptions/<sub-id>/resourceGroups/<ai-rg>/providers/Microsoft.MachineLearningServices/workspaces/<ai-project>"
   
   # Cognitive Services User role
   az role assignment create \
     --assignee <principal-id> \
     --role "Cognitive Services User" \
     --scope "/subscriptions/<sub-id>/resourceGroups/<ai-rg>/providers/Microsoft.CognitiveServices/accounts/<ai-resource>"
   ```

## Updating Your Deployment

### Deploy Code Changes Only

If you only modified application code:

```bash
azd deploy
```

This is faster as it skips infrastructure provisioning.

### Deploy Infrastructure Changes

If you modified Bicep templates:

```bash
# Preview changes first
azd provision --preview

# Apply changes
azd provision
```

### Deploy Everything

To redeploy both infrastructure and code:

```bash
azd up
```

## Monitoring and Troubleshooting

### View Application Logs

Stream logs in real-time:

```bash
# Using Azure CLI
az webapp log tail --name <app-service-name> --resource-group <resource-group-name>

# Or visit Azure Portal
# App Service → Monitoring → Log stream
```

### View Application Insights

Access telemetry data:

```bash
# Get Application Insights resource
azd env get-values | grep APPLICATIONINSIGHTS_CONNECTION_STRING

# Or visit Azure Portal
# Application Insights → Investigate → Logs/Metrics
```

### Health Check

Test the health endpoint:

```bash
curl https://<your-app-url>.azurewebsites.net/health
```

Expected response:
```json
{"status": "healthy"}
```

### Common Issues

**Issue: App Service returns 500 error**
- Check logs: `az webapp log tail`
- Verify `AZURE_AI_PROJECT_ENDPOINT` is set correctly
- Ensure managed identity has required permissions

**Issue: Authentication errors**
- Verify you're logged in: `az account show`
- Check managed identity is enabled: `az webapp identity show`
- Validate role assignments on AI Foundry resources

**Issue: Deployment fails**
- Check quota limits: `az vm list-usage --location <location>`
- Verify subscription has required providers registered
- Review deployment logs: `azd deploy --debug`

## Environment Management

### List Environments

```bash
azd env list
```

### View Environment Values

```bash
azd env get-values
```

### Switch Environments

```bash
azd env select <environment-name>
```

### Delete Environment and Resources

```bash
# Delete all Azure resources
azd down

# Delete without confirmation
azd down --force --purge
```

## Cost Management

### Estimated Costs (US East)

| SKU | Monthly Cost (approx.) |
|-----|------------------------|
| B1 (Basic) | $13 |
| B2 (Basic) | $26 |
| S1 (Standard) | $73 |
| P1v2 (Premium) | $80 |

Plus usage-based costs:
- Application Insights: ~$2-5/month (depends on telemetry volume)
- Log Analytics: ~$1-3/month (depends on log volume)

### Monitor Costs

View costs in Azure Portal:
- Cost Management → Cost Analysis
- Filter by Resource Group: `rg-<env>-<token>`

## CI/CD Integration

To integrate with GitHub Actions or Azure DevOps:

1. Create a service principal:
   ```bash
   az ad sp create-for-rbac --name "azure-pricing-assistant-cicd" --role contributor --scopes /subscriptions/<subscription-id>
   ```

2. Store credentials as secrets in your CI/CD platform

3. Use `azd` commands in your pipeline:
   ```yaml
   - name: Deploy to Azure
     run: |
       azd auth login --client-id ${{ secrets.AZURE_CLIENT_ID }} \
                      --client-secret ${{ secrets.AZURE_CLIENT_SECRET }} \
                      --tenant-id ${{ secrets.AZURE_TENANT_ID }}
       azd up --no-prompt
   ```

## Security Best Practices

1. **Use Key Vault for Secrets**: Store sensitive configuration in Azure Key Vault
2. **Enable HTTPS Only**: Already configured in Bicep templates
3. **Set Minimum TLS Version**: Already configured to TLS 1.2
4. **Disable FTP**: Already configured (FTPS disabled)
5. **Use Managed Identity**: Already configured for Azure AI Foundry access
6. **Monitor Security**: Enable Microsoft Defender for App Service

## Next Steps

- Configure custom domain: [Azure Docs](https://docs.microsoft.com/azure/app-service/app-service-web-tutorial-custom-domain)
- Set up SSL certificate: [Azure Docs](https://docs.microsoft.com/azure/app-service/configure-ssl-certificate)
- Configure authentication: [Azure Docs](https://docs.microsoft.com/azure/app-service/configure-authentication-provider-aad)
- Scale your application: [Azure Docs](https://docs.microsoft.com/azure/app-service/manage-scale-up)
