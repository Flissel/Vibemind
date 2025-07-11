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
if [ ! -d "models" ] || [ -z "$(ls -A models/*.gguf 2>/dev/null)" ]; then
    echo -e "${YELLOW}⚠️  Warning: No local LLM model found${NC}"
    echo ""
    echo -e "${GREEN}To download a model, run:${NC}"
    echo "./download_models.sh"
    echo ""
    echo "Or download manually:"
    echo "wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf -O models/llama-3.2-3b.gguf"
    echo ""
    echo "You can also use OpenAI by setting OPENAI_API_KEY environment variable"
    echo ""
    read -p "Continue with mock LLM for testing? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run the assistant
echo -e "${GREEN}Starting Sakana Desktop Assistant...${NC}"
echo ""
python src/main.py "$@"