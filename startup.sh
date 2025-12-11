#!/bin/bash

# Azure App Service startup script for Python application

echo "Starting Azure Pricing Assistant..."

# Dependencies and environment are managed by Oryx. No manual venv or pip install required.
echo "Starting Gunicorn server..."
# Gunicorn startup is handled by Azure App Service via appCommandLine in infra/resources.bicep
