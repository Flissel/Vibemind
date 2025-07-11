#!/bin/bash
# Helper script to update config.yaml

echo "Config Update Helper"
echo "==================="
echo ""
echo "1) Use local model"
echo "2) Use OpenAI"
echo "3) Use mock (testing)"
echo "4) Change temperature"
echo "5) Edit manually"
echo ""
read -p "Choose option (1-5): " choice

case $choice in
    1)
        echo "Available models in models/:"
        ls models/*.gguf 2>/dev/null | sed 's/models\///g' | sed 's/\.gguf//g'
        echo ""
        read -p "Enter model name (without .gguf): " model
        sed -i "s/llm_provider: .*/llm_provider: \"local\"/" config.yaml
        sed -i "s/model_name: .*/model_name: \"$model\"/" config.yaml
        echo "✅ Updated to use local model: $model"
        ;;
    2)
        read -p "Enter OpenAI model (gpt-4, gpt-3.5-turbo): " model
        sed -i "s/llm_provider: .*/llm_provider: \"openai\"/" config.yaml
        sed -i "s/model_name: .*/model_name: \"$model\"/" config.yaml
        echo "✅ Updated to use OpenAI: $model"
        echo "Don't forget to set: export OPENAI_API_KEY='your-key'"
        ;;
    3)
        sed -i "s/llm_provider: .*/llm_provider: \"mock\"/" config.yaml
        echo "✅ Updated to use mock LLM (testing mode)"
        ;;
    4)
        read -p "Enter temperature (0.1-1.0): " temp
        sed -i "s/temperature: .*/temperature: $temp/" config.yaml
        echo "✅ Updated temperature to: $temp"
        ;;
    5)
        ${EDITOR:-nano} config.yaml
        ;;
esac

echo ""
echo "Current settings:"
grep -E "llm_provider|model_name|temperature" config.yaml