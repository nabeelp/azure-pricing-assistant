# Quick Start Guide - Azure Pricing Assistant

## 🚀 Deploy to Azure in 5 Minutes

### Prerequisites
- Azure subscription
- Azure AI Foundry project endpoint
- [Azure Developer CLI (azd)](https://aka.ms/install-azd) installed

### Deployment Steps

```bash
# 1. Login to Azure
azd auth login

# 2. Create environment
azd env new prod

# 3. Set your AI Foundry endpoint
azd env set AZURE_AI_PROJECT_ENDPOINT "https://your-project.services.ai.azure.com/api/projects/your-project-prj"

# 4. Deploy!
azd up
```

### Post-Deployment

1. **Configure Permissions** (Required):
   ```bash
   # Get the App Service principal ID
   PRINCIPAL_ID=$(azd env get-values | grep principalId | cut -d'=' -f2)
   
   # Grant access to your AI Foundry project
   az role assignment create \
     --assignee $PRINCIPAL_ID \
     --role "Cognitive Services User" \
     --scope "<your-ai-resource-id>"
   ```

2. **Test Your Deployment**:
   ```bash
   # Get your app URL
   azd env get-values | grep AZURE_APP_SERVICE_URL
   
   # Open in browser
   open $(azd env get-values | grep AZURE_APP_SERVICE_URL | cut -d'=' -f2)
   ```

## 💻 Local Development

### Setup

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd azure-pricing-assistant

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set AZURE_AI_PROJECT_ENDPOINT

# 5. Login to Azure
az login

# 6. Run the app
python app.py
```

### Access the App
Open http://localhost:8000 in your browser

## 📊 Cost Estimate

| Configuration | Monthly Cost |
|--------------|--------------|
| Basic (B1) | ~$16-21 |
| Standard (S1) | ~$76-81 |
| Premium (P1v2) | ~$83-88 |

## 🔧 Common Commands

### Deployment
```bash
azd up              # Deploy everything
azd deploy          # Deploy code only
azd provision       # Deploy infrastructure only
azd down            # Delete all resources
```

### Monitoring
```bash
azd monitor         # Open monitoring dashboard
azd env get-values  # View configuration
```

### Logs
```bash
# Stream logs
az webapp log tail \
  --name $(azd env get-values | grep AZURE_APP_SERVICE_NAME | cut -d'=' -f2) \
  --resource-group $(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d'=' -f2)
```

## 📖 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment guide
- **[AZURE_SETUP.md](AZURE_SETUP.md)** - Complete setup summary
- **[README.md](README.md)** - Full project documentation
- **[specs/PRD.md](specs/PRD.md)** - Product requirements

## 🆘 Troubleshooting

### App returns 500 error
```bash
# Check logs
az webapp log tail --name <app-name> --resource-group <rg-name>

# Verify environment
azd env get-values
```

### Authentication fails
```bash
# Verify login
az account show

# Check managed identity
az webapp identity show --name <app-name> --resource-group <rg-name>
```

### Can't connect to AI Foundry
```bash
# Verify endpoint
azd env get-values | grep AZURE_AI_PROJECT_ENDPOINT

# Check permissions
az role assignment list --assignee <principal-id>
```

## 💡 Tips

1. **Use `--preview` first**: Always run `azd provision --preview` before deploying
2. **Monitor costs**: Set up budget alerts in Azure Portal
3. **Scale appropriately**: Start with B1, upgrade as needed
4. **Enable monitoring**: Application Insights is configured by default
5. **Secure secrets**: Use Azure Key Vault for production

## 🎯 Next Steps

After successful deployment:

1. ✅ Test the web interface
2. ✅ Verify AI Foundry connectivity
3. ✅ Run a complete pricing workflow
4. ✅ Check Application Insights for telemetry
5. ✅ Set up custom domain (optional)
6. ✅ Configure authentication (optional)
7. ✅ Set up CI/CD (optional)

## 🔗 Quick Links

- [Azure Portal](https://portal.azure.com)
- [Azure AI Foundry](https://ai.azure.com)
- [azd Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [App Service Documentation](https://learn.microsoft.com/azure/app-service/)
