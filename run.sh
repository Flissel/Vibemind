#!/bin/bash
# Quick start script for Sakana Desktop Assistant

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐟 Sakana Desktop Assistant - Quick Start${NC}"
echo "========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "Python version: ${YELLOW}$python_version${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies if needed
if [ ! -f ".installed" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    touch .installed
fi

# Create necessary directories
mkdir -p data models plugins

# Check for LLM model
if [ ! -f "models/llama-3.2-3b.gguf" ]; then
    echo -e "${YELLOW}⚠️  Warning: No local LLM model found${NC}"
    echo "To use local LLM, download a GGUF model to the models/ directory"
    echo "Example: wget https://huggingface.co/[model-path]/resolve/main/model.gguf -O models/llama-3.2-3b.gguf"
    echo ""
    echo "You can also use OpenAI by setting OPENAI_API_KEY environment variable"
fi

# Run the assistant
echo -e "${GREEN}Starting Sakana Desktop Assistant...${NC}"
echo ""
python src/main.py "$@"