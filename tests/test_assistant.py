#!/usr/bin/env python3
"""Test script for Sakana Desktop Assistant"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core import Config, SakanaAssistant

async def test_assistant():
    """Test basic assistant functionality"""
    
    print("🧪 Testing Sakana Desktop Assistant")
    print("="*50)
    
    # Create config
    config = Config()
    config.llm_provider = "mock"  # Use mock LLM for testing
    
    # Initialize assistant
    assistant = SakanaAssistant(config)
    await assistant.initialize()
    
    print("✅ Assistant initialized successfully")
    
    # Test some interactions
    test_inputs = [
        "Hello, can you help me?",
        "List files in the current directory",
        "What's the CPU usage?",
        "Create a task: Test the assistant",
        "Show system information"
    ]
    
    for user_input in test_inputs:
        print(f"\n👤 User: {user_input}")
        
        result = await assistant.process_request(user_input)
        
        if result['success']:
            response = result['response']
            print(f"🐟 Sakana: {response['content']}")
            print(f"⏱️  Response time: {result['response_time']:.2f}s")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    # Show stats
    print("\n📊 Final Statistics:")
    print(f"Requests handled: {assistant.metrics['requests_handled']}")
    print(f"Successful: {assistant.metrics['successful_completions']}")
    print(f"Patterns learned: {assistant.metrics['patterns_learned']}")
    
    # Shutdown
    await assistant.shutdown()
    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_assistant())