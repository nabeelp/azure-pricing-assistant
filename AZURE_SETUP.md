# Azure Deployment Setup - Summary

## What Was Done

This project has been configured for Azure deployment using Azure Developer CLI (azd). The application now runs as a web service on Azure App Service.

## Key Changes

### 1. Infrastructure as Code
- **Created**: `infra/main.bicep` - Main infrastructure deployment template
- **Created**: `infra/resources.bicep` - Resource definitions for App Service, Application Insights, Log Analytics
- **Created**: `infra/main.parameters.json` - Deployment parameters with environment variable substitution

### 2. Web Application
- **Created**: `app.py` - Flask web application with REST API endpoints
- **Created**: `templates/index.html` - Modern web UI for interactive chat
- **Features**:
  - Real-time chat interface for requirements gathering
  - Session management for multi-turn conversations
  - "Generate Proposal" workflow for BOM → Pricing → Proposal
  - Health check endpoint at `/health`

### 3. Azure Developer CLI Configuration
- **Created**: `azure.yaml` - azd service definition
- **Configured**: Gunicorn as the production WSGI server with 4 workers

### 4. Deployment Scripts
- **Created**: `startup.sh` - App Service startup script
- **Created**: `.dockerignore` - Files to exclude from deployment
- **Updated**: `.gitignore` - Added test files and additional ignore patterns
- **Updated**: `requirements.txt` - Added Flask and Gunicorn dependencies

### 5. Documentation
- **Created**: `DEPLOYMENT.md` - Comprehensive deployment guide
- **Created**: `.env.example` - Environment variable template
- **Updated**: `README.md` - Added Azure deployment sections
- **Updated**: `.github/copilot-instructions.md` - Added Azure deployment guidelines

## Azure Resources Created

When deployed, the following Azure resources are provisioned:

| Resource Type | Name Pattern | Purpose |
|---------------|-------------|---------|
| Resource Group | `rg-<env>-<token>` | Container for all resources |
| App Service Plan | `asp-<env>-<token>` | Compute for web app (Linux, configurable SKU) |
| App Service | `app-<env>-<token>` | Hosts the Flask application |
| Application Insights | `appi-<env>-<token>` | Monitoring and telemetry |
| Log Analytics Workspace | `log-<env>-<token>` | Log aggregation |

## Deployment Commands

### Initial Deployment
```bash
azd auth login
azd env new <environment-name>
azd env set AZURE_AI_PROJECT_ENDPOINT "<your-endpoint>"
azd provision --preview  # Preview changes
azd up                   # Deploy everything
```

### Update Deployment
```bash
azd deploy               # Deploy code changes only
azd provision            # Deploy infrastructure changes
azd up                   # Deploy both
```

### Cleanup
```bash
azd down                 # Delete all resources
```

## Environment Variables

The following environment variables are configured in App Service:

| Variable | Source | Purpose |
|----------|--------|---------|
| `AZURE_AI_PROJECT_ENDPOINT` | azd environment | Azure AI Foundry endpoint |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Auto-configured | Application Insights telemetry |
| `FLASK_SECRET_KEY` | Auto-generated | Flask session encryption |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | Auto-configured | Enable Oryx build |
| `ENABLE_ORYX_BUILD` | Auto-configured | Enable Oryx build |

## Security Features

1. **Managed Identity**: System-assigned identity for Azure AI Foundry authentication
2. **HTTPS Only**: Enforced at App Service level
3. **TLS 1.2**: Minimum TLS version configured
4. **FTPS Disabled**: Secure deployment only
5. **No Hardcoded Secrets**: All credentials via environment variables

## Monitoring

### Application Insights
- Automatic instrumentation via OpenTelemetry
- Request tracing and performance metrics
- Exception tracking and logging

### Log Analytics
- Centralized log aggregation
- Query logs with KQL (Kusto Query Language)
- Alert rules and dashboards

### Health Check
- Endpoint: `GET /health`
- Returns: `{"status": "healthy"}`
- Use for liveness probes and monitoring

## Cost Estimate

**Minimum Configuration (B1 SKU)**:
- App Service Plan (B1): ~$13/month
- Application Insights: ~$2-5/month
- Log Analytics: ~$1-3/month
- **Total**: ~$16-21/month

**Recommended Configuration (S1 SKU)**:
- App Service Plan (S1): ~$73/month
- Application Insights: ~$2-5/month
- Log Analytics: ~$1-3/month
- **Total**: ~$76-81/month

## Testing the Deployment

### 1. Local Testing
```bash
# Set environment variables
export AZURE_AI_PROJECT_ENDPOINT="<your-endpoint>"

# Run the app
python app.py

# Visit http://localhost:8000
```

### 2. Azure Testing
```bash
# Get the deployed URL
azd env get-values | grep AZURE_APP_SERVICE_URL

# Test health endpoint
curl https://<your-app>.azurewebsites.net/health

# Visit the web UI
open https://<your-app>.azurewebsites.net
```

## Required Permissions

After deployment, grant the App Service managed identity access to Azure AI Foundry:

```bash
# Get the managed identity principal ID
PRINCIPAL_ID=$(az webapp identity show \
  --name <app-name> \
  --resource-group <rg-name> \
  --query principalId -o tsv)

# Grant Reader role on AI project
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Reader" \
  --scope "<ai-project-resource-id>"

# Grant Cognitive Services User role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Cognitive Services User" \
  --scope "<ai-resource-id>"
```

## Troubleshooting

### Common Issues

1. **500 Internal Server Error**
   - Check logs: `az webapp log tail`
   - Verify environment variables are set
   - Ensure managed identity has permissions

2. **Module Import Errors**
   - Verify `requirements.txt` is complete
   - Check deployment logs for build errors
   - Ensure Oryx build is enabled

3. **Authentication Failures**
   - Verify `AZURE_AI_PROJECT_ENDPOINT` is correct
   - Check managed identity role assignments
   - Test with `az account show`

### Viewing Logs
```bash
# Stream application logs
az webapp log tail --name <app-name> --resource-group <rg-name>

# Download logs
az webapp log download --name <app-name> --resource-group <rg-name>

# View in Azure Portal
# App Service → Monitoring → Log stream
```

## Next Steps

1. **Deploy to Azure**:
   - Follow instructions in `DEPLOYMENT.md`
   - Start with `azd provision --preview` to see what will be created

2. **Configure Permissions**:
   - Grant managed identity access to Azure AI Foundry
   - Test authentication from App Service

3. **Test the Application**:
   - Visit the deployed URL
   - Run through a complete workflow
   - Monitor Application Insights

4. **Set Up CI/CD** (Optional):
   - Configure GitHub Actions or Azure DevOps
   - Automate deployments on git push

5. **Production Hardening** (Optional):
   - Configure custom domain
   - Set up SSL certificate
   - Enable authentication (Azure AD)
   - Configure autoscaling
   - Set up monitoring alerts

## Support

- **Deployment Issues**: See `DEPLOYMENT.md`
- **Application Issues**: See `README.md`
- **Development Guidelines**: See `.github/copilot-instructions.md`
- **Agent Behavior**: See `specs/PRD.md`

## Files Modified/Created

### Created Files
- `app.py` - Flask web application
- `templates/index.html` - Web UI
- `infra/main.bicep` - Main infrastructure template
- `infra/resources.bicep` - Resource definitions
- `infra/main.parameters.json` - Deployment parameters
- `azure.yaml` - azd configuration
- `startup.sh` - App Service startup script
- `.dockerignore` - Deployment ignore patterns
- `DEPLOYMENT.md` - Deployment guide
- `.env.example` - Environment variable template

### Modified Files
- `requirements.txt` - Added Flask, Gunicorn
- `.gitignore` - Added test files
- `README.md` - Added Azure deployment sections
- `.github/copilot-instructions.md` - Added deployment guidelines

### Preserved Files
- `main.py` - Original CLI application (still works)
- All agent implementations - Unchanged
- `specs/PRD.md` - Agent specifications unchanged
