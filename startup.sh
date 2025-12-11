#!/bin/bash

# Azure App Service startup script for Python application

echo "Starting Azure Pricing Assistant..."

# Install dependencies if not already installed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Starting Gunicorn server..."
# Gunicorn startup is handled by Azure App Service via appCommandLine in infra/resources.bicep
