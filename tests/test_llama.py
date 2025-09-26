#!/usr/bin/env python3
"""Test Llama model directly

This test requires the optional dependency `llama_cpp` and a local GGUF model file.
If `llama_cpp` is not available, we skip the test at collection time to avoid
failing the full test suite in environments without the optional dependency.
"""

# Guard optional import so pytest can skip this module cleanly
try:
    from llama_cpp import Llama  # type: ignore
except Exception:  # ImportError or any environment-related import failure
    try:
        import pytest  # type: ignore
        pytest.skip(
            "llama_cpp not installed or failed to import; skipping test_llama.py",
            allow_module_level=True,
        )
    except Exception:
        # Fallback when pytest is unavailable: exit without error so `python test_llama.py` also works
        print("llama_cpp not installed; skipping test_llama.py")
        raise SystemExit(0)

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