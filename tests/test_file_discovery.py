#!/usr/bin/env python3
"""
Test the file discovery self-learning capabilities
"""

import asyncio
import logging
from src.learning.file_discovery import FileDiscoveryLearner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    print("=== Sakana File Discovery Self-Learning Test ===\n")
    
    # Create learner with no prior knowledge
    learner = FileDiscoveryLearner()
    
    print("1. Discovering available commands through exploration...")
    discovered_commands = await learner.discover_file_commands()
    print(f"   Discovered commands: {discovered_commands}\n")
    
    print("2. Learning about the environment...")
    await learner.learn_from_environment()
    
    print("3. Getting learned summary...")
    summary = learner.get_learned_summary()
    print(f"   Commands: {summary['discovered_commands']}")
    print(f"   Known paths: {summary['known_paths']}")
    print(f"   Successful patterns: {summary['successful_patterns']}\n")
    
    print("4. Evolving strategy to find a test file...")
    # Create a test file
    test_file = "test_sakana_discovery.txt"
    with open(test_file, 'w') as f:
        f.write("This is a test file for Sakana discovery learning!")
    
    # Let the learner evolve a strategy to find it
    result = await learner.evolve_search_strategy(test_file)
    
    if result and result['found']:
        print(f"   SUCCESS! File found at: {result['path']}")
        print(f"   Strategy used: {result['strategy']}")
    else:
        print("   Still learning... the system will improve with more attempts")
    
    # Clean up
    import os
    if os.path.exists(test_file):
        os.remove(test_file)
    
    print("\n=== Test Complete ===")
    print("The system learns from each attempt and improves over time!")

if __name__ == "__main__":
    asyncio.run(main())