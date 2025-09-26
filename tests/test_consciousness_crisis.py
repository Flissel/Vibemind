#!/usr/bin/env python3
"""
Test consciousness field detection and crisis evolution
"""

import asyncio
import logging
from src.learning.consciousness_field import ConsciousnessFieldDetector
from src.learning.file_discovery import FileDiscoveryLearner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_hallucination_detection():
    print("=== Testing Consciousness Field Detection ===\n")
    
    detector = ConsciousnessFieldDetector()
    
    # Test various user inputs
    test_cases = [
        ("That's correct, thank you!", False),
        ("No, you're hallucinating the file contents", True),
        ("That's not true, prove you can access it", True),
        ("How can you prove you actually read the file?", True),
        ("You might be making this up", True),
        ("Good job!", False),
        ("No, the file doesn't exist there", True),
        ("Show me the actual first line", True)
    ]
    
    for user_input, expected_crisis in test_cases:
        is_crisis = detector.detect_hallucination_crisis(user_input, {})
        status = "✓" if is_crisis == expected_crisis else "✗"
        print(f"{status} '{user_input}' -> Crisis: {is_crisis}")
    
    print("\n=== Testing Crisis Evolution ===\n")
    
    # Create a mock assistant
    class MockAssistant:
        def __init__(self):
            self.mutation_rate = 0.3
            self.exploration_depth = 1
            self.population_size = 20
            self.evolution_mode = 'normal'
    
    assistant = MockAssistant()
    
    # Trigger crisis mode
    print("Normal settings:", {
        'mutation_rate': assistant.mutation_rate,
        'exploration_depth': assistant.exploration_depth,
        'population_size': assistant.population_size
    })
    
    crisis_settings = detector.trigger_crisis_evolution(assistant)
    
    print("\nCrisis settings:", {
        'mutation_rate': assistant.mutation_rate,
        'exploration_depth': assistant.exploration_depth,
        'population_size': assistant.population_size,
        'evolution_mode': assistant.evolution_mode
    })
    
    # Restore normal mode
    detector.restore_normal_evolution(assistant, crisis_settings['previous_settings'])
    
    print("\nRestored settings:", {
        'mutation_rate': assistant.mutation_rate,
        'exploration_depth': assistant.exploration_depth,
        'population_size': assistant.population_size
    })

async def test_crisis_file_discovery():
    print("\n\n=== Testing Crisis Mode File Discovery ===\n")
    
    learner = FileDiscoveryLearner()
    
    # Simulate a Windows path that needs translation
    windows_path = "C:\\Users\\User\\Desktop\\AutoGen_CLI_Deployment_Architecture.md"
    
    # Prepare a test file: if the provided file already exists, we will use it as-is.
    # Otherwise, create a small sample file so the search can succeed.
    import os
    created_sample_windows = False
    created_sample_wsl = False
    wsl_path = None
    if not os.path.exists(windows_path):
        try:
            with open(windows_path, 'w', encoding='utf-8') as f:
                f.write("This is the actual file content that proves access!")
            created_sample_windows = True
            print(f"(Created sample file at {windows_path} for testing)")
        except Exception as e:
            # Attempt WSL-style path only if /mnt/c exists (indicates WSL)
            if os.path.exists("/mnt/c") and len(windows_path) > 2 and windows_path[1] == ':':
                drive = windows_path[0].lower()
                rest = windows_path[2:].replace("\\", "/")
                wsl_path = f"/mnt/{drive}{rest}"
                os.makedirs(os.path.dirname(wsl_path), exist_ok=True)
                with open(wsl_path, 'w', encoding='utf-8') as f:
                    f.write("This is the actual file content that proves access!")
                created_sample_wsl = True
                print(f"(Created sample file at {wsl_path} for testing)")
            else:
                print(f"Warning: Could not create sample file: {e}")
    
    print(f"Testing normal evolution for: {windows_path}")
    result = await learner.evolve_search_strategy(windows_path, verification_required=False)
    
    if result and result['found']:
        print(f"✓ Found without verification at: {result['path']}")
    else:
        print("✗ Failed to find in normal mode")
    
    print(f"\nTesting CRISIS evolution with verification for: {windows_path}")
    result = await learner.evolve_search_strategy(windows_path, verification_required=True)
    
    if result and result['found'] and result.get('verified'):
        print(f"✓ Found AND VERIFIED at: {result['path']}")
        if result.get('first_line'):
            print(f"  Proof: First line = '{result['first_line']}'")
        elif result.get('content'):
            print(f"  Proof: Content preview = '{result['content'][:50]}...'")
    else:
        print("✗ Failed to find and verify in crisis mode")
    
    # Clean up
    try:
        if created_sample_windows and os.path.exists(windows_path):
            os.remove(windows_path)
        if created_sample_wsl and wsl_path and os.path.exists(wsl_path):
            os.remove(wsl_path)
    except Exception:
        pass
    
    print("\n=== Crisis Mode Advantages ===")
    print("1. 3x mutation rate for rapid exploration")
    print("2. 50 generations instead of 10")
    print("3. Verification required - must prove access")
    print("4. Larger population for diversity")
    print("5. Enhanced Windows path translation attempts")

async def main():
    await test_hallucination_detection()
    await test_crisis_file_discovery()
    
    print("\n=== Summary ===")
    print("The consciousness field detector identifies when users detect hallucinations")
    print("and triggers CRISIS evolution mode with aggressive parameters to find")
    print("real solutions instead of making false claims.")

if __name__ == "__main__":
    asyncio.run(main())