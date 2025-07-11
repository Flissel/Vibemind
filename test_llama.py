#!/usr/bin/env python3
"""Test Llama model directly"""

from llama_cpp import Llama
import sys

print("Testing Llama model...")

# Load model
model_path = "models/llama-3.2-3b.gguf"
print(f"Loading model from: {model_path}")

try:
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,
        n_threads=8,
        verbose=False
    )
    print("Model loaded successfully!")
    
    # Test generation
    prompt = "Hello! How are you?"
    print(f"\nPrompt: {prompt}")
    print("Generating response...")
    
    response = llm(
        prompt,
        max_tokens=50,
        temperature=0.7,
        stop=["User:", "\n\n"],
        echo=False
    )
    
    print(f"\nResponse structure: {response.keys()}")
    print(f"\nGenerated text: {response['choices'][0]['text']}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()