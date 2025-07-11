# Using Local GGUF Models with Sakana Desktop Assistant

## Quick Start

Run the download script:
```bash
./download_models.sh
```

## What are GGUF Models?

GGUF (GPT-Generated Unified Format) is a format for running Large Language Models locally on your computer. Benefits:
- **Privacy**: All processing happens on your machine
- **No API costs**: Free to use once downloaded
- **Offline capable**: Works without internet
- **Fast**: Optimized for CPU/GPU inference

## Recommended Models

### For Most Users: Llama 3.2 3B
- **Size**: ~2GB
- **Performance**: Excellent balance of quality and speed
- **Download**:
```bash
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf -O models/llama-3.2-3b.gguf
```

### For Limited Resources: TinyLlama 1.1B
- **Size**: ~638MB
- **Performance**: Good for basic tasks
- **Download**:
```bash
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -O models/tinyllama-1.1b.gguf
```

### For Best Quality: Mistral 7B
- **Size**: ~4GB
- **Performance**: High quality responses
- **RAM Required**: 8GB+
- **Download**:
```bash
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf -O models/mistral-7b.gguf
```

## Manual Download Steps

1. **Create models directory**:
```bash
mkdir -p models
```

2. **Choose a model from HuggingFace**:
   - Visit: https://huggingface.co/models?library=gguf
   - Look for models with "GGUF" in the name
   - Check the Files tab for .gguf files

3. **Download the model**:
```bash
# Example for Llama 3.2
cd models
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

4. **Configure the assistant**:
Create or edit `config.yaml`:
```yaml
llm_provider: "local"
model_name: "Llama-3.2-3B-Instruct-Q4_K_M"  # Without .gguf extension
```

## Understanding Quantization

GGUF models come in different quantization levels:
- **Q4_K_M**: Recommended - good balance (4-bit)
- **Q5_K_M**: Better quality, larger size (5-bit)
- **Q8_0**: Near full quality, much larger (8-bit)
- **Q2_K**: Smallest size, lower quality (2-bit)

## System Requirements

| Model Size | RAM Required | Disk Space |
|------------|--------------|------------|
| 0.5B       | 2GB          | 400MB      |
| 1B         | 3GB          | 700MB      |
| 3B         | 6GB          | 2GB        |
| 7B         | 10GB         | 4GB        |
| 13B        | 16GB         | 8GB        |

## Installing llama-cpp-python

To use local models, install the Python bindings:

```bash
# Basic CPU installation
pip install llama-cpp-python

# With CUDA support (NVIDIA GPUs)
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python

# With Metal support (Apple Silicon)
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python

# With OpenBLAS (faster CPU)
CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python
```

## Finding More Models

### Popular GGUF Repositories:
1. **TheBloke**: https://huggingface.co/TheBloke
2. **Bartowski**: https://huggingface.co/bartowski  
3. **LoneStriker**: https://huggingface.co/LoneStriker
4. **Microsoft**: https://huggingface.co/microsoft

### Search for GGUF models:
https://huggingface.co/models?sort=downloads&search=gguf

## Troubleshooting

### Model not loading:
- Check file exists: `ls models/`
- Verify config.yaml has correct model_name
- Ensure enough RAM available

### Slow performance:
- Try smaller quantization (Q2_K or Q3_K)
- Use smaller model (TinyLlama)
- Enable GPU acceleration if available

### Out of memory:
- Use smaller model
- Close other applications
- Try Q2_K quantization

## Example Configuration

`config.yaml`:
```yaml
# LLM Settings
llm_provider: "local"
model_name: "llama-3.2-3b"  # Matches filename without .gguf
temperature: 0.7
max_tokens: 2048

# Performance Settings (optional)
context_size: 4096
threads: 8  # CPU threads to use
gpu_layers: 0  # Set to 20-35 for GPU acceleration
```

## Testing Your Model

After downloading, test it:
```bash
python test_assistant.py
```

Or run the full assistant:
```bash
./run.sh
```

The assistant will now use your local model for all interactions!