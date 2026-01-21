# Playwright MCP Deployment Guide

## Overview

This document provides guidance for deploying Playwright MCP in production environments to support the Azure Pricing Assistant's calculator automation functionality.

## Local Development (STDIO)

For local development, Playwright MCP uses STDIO transport which requires no separate server:

1. **Install Playwright MCP**:
   ```bash
   npm install -g @playwright/mcp
   ```

2. **Configure Environment**:
   ```bash
   # In .env file
   PLAYWRIGHT_MCP_TRANSPORT=stdio  # Default
   ```

3. **Run Application**:
   The application will automatically spawn Playwright MCP via STDIO when needed.

## Production Deployment (HTTP via Azure Container Apps)

For production environments, deploy Playwright MCP as a separate HTTP server in Azure Container Apps.

### Prerequisites

- Azure subscription with Container Apps capability
- Azure Container Registry (ACR) or Docker Hub access
- Azure CLI installed and authenticated

### Deployment Steps

1. **Build Container Image**:
   ```bash
   # Create Dockerfile for Playwright MCP
   cat > Dockerfile.playwright <<EOF
   FROM node:18-alpine
   
   RUN npm install -g @playwright/mcp
   RUN npx playwright install --with-deps chromium
   
   EXPOSE 8080
   
   CMD ["npx", "@playwright/mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8080"]
   EOF
   
   # Build and push to ACR
   docker build -f Dockerfile.playwright -t <your-acr>.azurecr.io/playwright-mcp:latest .
   docker push <your-acr>.azurecr.io/playwright-mcp:latest
   ```

2. **Deploy to Azure Container Apps**:
   ```bash
   # Create Container App
   az containerapp create \
     --name playwright-mcp \
     --resource-group <your-rg> \
     --environment <your-env> \
     --image <your-acr>.azurecr.io/playwright-mcp:latest \
     --target-port 8080 \
     --ingress external \
     --cpu 1.0 \
     --memory 2.0Gi
   ```

3. **Configure Main Application**:
   Set environment variables:
   - `PLAYWRIGHT_MCP_TRANSPORT=http`
   - `PLAYWRIGHT_MCP_URL=https://<playwright-mcp-url>.azurecontainerapps.io`

## Infrastructure as Code

Add to `infra/resources.bicep`:

```bicep
resource playwrightMCP 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'playwright-mcp-${environmentName}'
  location: location
  properties: {
    environmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8080
      }
    }
    template: {
      containers: [
        {
          name: 'playwright-mcp'
          image: '${acrName}.azurecr.io/playwright-mcp:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
    }
  }
}
```

## Migration Checklist

- [ ] Install Playwright MCP for local dev (`npm install -g @playwright/mcp`)
- [ ] Build and push container image
- [ ] Deploy Container App
- [ ] Configure App Service environment variables
- [ ] Test end-to-end pricing workflow
- [ ] Set up monitoring

## References

- [Playwright MCP GitHub](https://github.com/microsoft/playwright-mcp)
- [Azure Container Apps Docs](https://learn.microsoft.com/azure/container-apps/)
