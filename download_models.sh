#!/bin/bash
# Script to download popular GGUF models for local use

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 GGUF Model Downloader for Sakana Desktop Assistant${NC}"
echo "=================================================="
echo ""
echo "Select a model to download:"
echo ""
echo "1) Llama 3.2 3B (Recommended - 2GB)"
echo "2) Phi-3 Mini (Fast - 2.4GB)"
echo "3) Mistral 7B (Powerful - 4GB)"
echo "4) TinyLlama 1.1B (Tiny - 638MB)"
echo "5) Qwen 2.5 0.5B (Very small - 394MB)"
echo "6) Custom URL"
echo ""
read -p "Enter your choice (1-6): " choice

cd "$(dirname "$0")"
mkdir -p models

case $choice in
    1)
        echo -e "${YELLOW}Downloading Llama 3.2 3B...${NC}"
        wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
             -O models/llama-3.2-3b.gguf
        MODEL_NAME="llama-3.2-3b"
        ;;
    2)
        echo -e "${YELLOW}Downloading Phi-3 Mini...${NC}"
        wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf \
             -O models/phi-3-mini.gguf
        MODEL_NAME="phi-3-mini"
        ;;
    3)
        echo -e "${YELLOW}Downloading Mistral 7B...${NC}"
        wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf \
             -O models/mistral-7b.gguf
        MODEL_NAME="mistral-7b"
        ;;
    4)
        echo -e "${YELLOW}Downloading TinyLlama 1.1B...${NC}"
        wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
             -O models/tinyllama-1.1b.gguf
        MODEL_NAME="tinyllama-1.1b"
        ;;
    5)
        echo -e "${YELLOW}Downloading Qwen 2.5 0.5B...${NC}"
        wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf \
             -O models/qwen-2.5-0.5b.gguf
        MODEL_NAME="qwen-2.5-0.5b"
        ;;
    6)
        read -p "Enter the GGUF model URL: " MODEL_URL
        read -p "Enter a name for the model file (without .gguf): " MODEL_NAME
        echo -e "${YELLOW}Downloading custom model...${NC}"
        wget "$MODEL_URL" -O "models/${MODEL_NAME}.gguf"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Model downloaded successfully!${NC}"
    echo ""
    echo "To use this model, update your config.yaml:"
    echo -e "${YELLOW}model_name: \"${MODEL_NAME}\"${NC}"
    echo ""
    echo "Or create a config.yaml file with:"
    echo "llm_provider: \"local\""
    echo "model_name: \"${MODEL_NAME}\""
else
    echo -e "${RED}❌ Download failed${NC}"
    exit 1
fi