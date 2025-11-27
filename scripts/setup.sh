#!/bin/bash

# Chronos Setup Script
# This script sets up the development environment

set -e

echo "🤖 Setting up Chronos Autonomous Scheduling Agent..."
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Error: Python 3.10+ required. Found: $python_version"
    exit 1
fi

echo "✓ Python $python_version detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

echo "✓ Dependencies installed"
echo ""

# Set up environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cat > .env << 'EOF'
# API Keys
HUGGINGFACE_TOKEN=your_hf_token_here
OPENAI_API_KEY=your_openai_key_here

# Google APIs
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Application Settings
ENV=development
DEBUG=true
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Model Configuration
LLAMA_MODEL_NAME=meta-llama/Meta-Llama-3-8B-Instruct
LLAMA_QUANTIZATION=4bit
MAX_NEW_TOKENS=512
TEMPERATURE=0.7
EOF
    echo "✓ .env file created"
    echo ""
    echo "⚠️  Please edit .env and add your API keys:"
    echo "   - HuggingFace token (for Llama 3 access)"
    echo "   - Google Cloud credentials"
    echo ""
else
    echo "✓ .env file already exists"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p data/training data/logs models

echo "✓ Directories created"
echo ""

# Download or setup credentials template
if [ ! -f credentials.json ]; then
    echo "Note: You'll need to download credentials.json from Google Cloud Console"
    echo "  1. Go to https://console.cloud.google.com/"
    echo "  2. Create OAuth 2.0 credentials"
    echo "  3. Download as credentials.json"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Download credentials.json from Google Cloud Console (if using Gmail/Calendar)"
echo "  3. Run the demo: python scripts/demo.py"
echo "  4. Start the API server: python -m uvicorn src.chronos.api.app:app --reload"
echo ""
echo "For more information, see README.md"

