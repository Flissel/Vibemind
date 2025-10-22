# -*- coding: utf-8 -*-
"""
Model client utilities for MCP agents.
Provides unified model client creation for OpenAI-compatible APIs.
"""
import os
from autogen_ext.models.openai import OpenAIChatCompletionClient


def get_model_client(model: str) -> OpenAIChatCompletionClient:
    """
    Create an OpenAI-compatible chat completion client.

    Args:
        model: Model identifier (e.g., "gpt-4o", "openai/gpt-4o-mini", "llama3.1")

    Returns:
        OpenAIChatCompletionClient instance configured for the specified model

    Environment Variables:
        OPENAI_API_KEY: API key for OpenAI or compatible service
        OPENAI_BASE_URL: Optional base URL for API (e.g., for local models)
        OPENAI_MODEL: Optional default model override

    Examples:
        >>> client = get_model_client("gpt-4o")
        >>> client = get_model_client("openai/gpt-4o-mini")
    """
    # Extract model name if it has a prefix (e.g., "openai/gpt-4o-mini" -> "gpt-4o-mini")
    if "/" in model:
        model_name = model.split("/", 1)[1]
    else:
        model_name = model

    # Get API configuration from environment
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL")  # Optional, for local models

    # Create client with optional base_url
    if base_url:
        client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=api_key,
            base_url=base_url
        )
    else:
        client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=api_key
        )

    return client


def get_default_model() -> str:
    """
    Get the default model from environment or use fallback.

    Returns:
        Model identifier string

    Environment Variables:
        OPENAI_MODEL: Preferred model name
        MODEL: Alternative model name variable
        OPENAI_BASE_URL: If set, defaults to "llama3.1" for local inference

    Fallback:
        - "gpt-4o" if using OpenAI API
        - "llama3.1" if using local inference (OPENAI_BASE_URL set)
    """
    # Check environment variables
    model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL")

    if model:
        return model

    # Fallback based on whether we're using local inference
    if os.getenv("OPENAI_BASE_URL"):
        return "llama3.1"  # Common local model
    else:
        return "gpt-4o"  # OpenAI default


if __name__ == "__main__":
    # Test model client creation
    print("Testing model client creation...")

    test_model = get_default_model()
    print(f"Default model: {test_model}")

    try:
        client = get_model_client(test_model)
        print(f"✓ Successfully created client for model: {test_model}")
        print(f"  Type: {type(client).__name__}")
    except Exception as e:
        print(f"✗ Error creating client: {e}")
