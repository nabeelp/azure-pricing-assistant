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
gunicorn --bind=0.0.0.0:8000 --workers=4 --threads=2 --timeout=120 --access-logfile=- --error-logfile=- app:app
