"""
Test Tahlamus Integration

Tests the integration between Sakana and Tahlamus cognitive architecture.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tahlamus import TAHLAMUS_AVAILABLE, TAHLAMUS_PATH
from tahlamus.bridge import TahalamusBridge, create_tahlamus_bridge


def test_tahlamus_path_detection():
    """Test that Tahlamus path is correctly detected"""
    print(f"Tahlamus available: {TAHLAMUS_AVAILABLE}")
    print(f"Tahlamus path: {TAHLAMUS_PATH}")

    if TAHLAMUS_AVAILABLE:
        assert TAHLAMUS_PATH.exists(), f"Tahlamus path should exist: {TAHLAMUS_PATH}"
        assert (TAHLAMUS_PATH / "core").exists(), "Tahlamus core/ directory should exist"
        assert (TAHLAMUS_PATH / "production").exists(), "Tahlamus production/ directory should exist"
    else:
        print(f"⚠️  Tahlamus not found at {TAHLAMUS_PATH}")
        print(f"   Clone from: https://github.com/Flissel/the_brain.git")


def test_tahlamus_bridge_creation():
    """Test creating a TahalamusBridge instance"""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    bridge = create_tahlamus_bridge(data_dir=data_dir)

    assert bridge is not None
    assert bridge.data_dir == data_dir
    assert bridge.user_id == "sakana_main"

    if TAHLAMUS_AVAILABLE:
        assert bridge.is_available(), "Bridge should be available when Tahlamus is present"
        print("✓ TahalamusBridge initialized successfully")
    else:
        assert not bridge.is_available(), "Bridge should not be available without Tahlamus"
        print("⚠️  TahalamusBridge created but Tahlamus not available")


@pytest.mark.skipif(not TAHLAMUS_AVAILABLE, reason="Tahlamus not available")
def test_tahlamus_prediction():
    """Test basic prediction through Tahlamus"""
    data_dir = Path(__file__).parent.parent / "data"
    bridge = create_tahlamus_bridge(data_dir=data_dir)

    # Process a simple request
    prediction = bridge.process_request("Open Excel")

    assert prediction is not None, "Should receive a prediction"
    assert hasattr(prediction, 'actionable_decision'), "Should have actionable_decision"
    assert hasattr(prediction, 'memory_context'), "Should have memory_context"

    print(f"\n✓ Tahlamus Prediction:")
    print(f"  - Action: {prediction.actionable_decision.primary_action}")
    print(f"  - Confidence: {prediction.actionable_decision.confidence:.2f}")
    print(f"  - Task Type: {prediction.task_type}")


@pytest.mark.skipif(not TAHLAMUS_AVAILABLE, reason="Tahlamus not available")
def test_memory_context_retrieval():
    """Test memory context retrieval"""
    data_dir = Path(__file__).parent.parent / "data"
    bridge = create_tahlamus_bridge(data_dir=data_dir)

    memory_context = bridge.get_memory_context("Create a report")

    assert isinstance(memory_context, dict), "Should return a dictionary"
    print(f"\n✓ Memory Context Retrieved:")
    print(f"  - Working Memory: {memory_context.get('working_memory_size', 0)} items")
    print(f"  - Episodic Memory: {memory_context.get('episodic_memory_size', 0)} items")


@pytest.mark.skipif(not TAHLAMUS_AVAILABLE, reason="Tahlamus not available")
def test_learning_from_outcome():
    """Test learning from execution outcome"""
    data_dir = Path(__file__).parent.parent / "data"
    bridge = create_tahlamus_bridge(data_dir=data_dir)

    # Give feedback
    bridge.learn_from_outcome(
        task="Open Excel",
        predicted_action="open_application",
        actual_action="open_application",
        success=True,
        execution_time_ms=250.0
    )

    print("\n✓ Tahlamus learned from successful outcome")


@pytest.mark.skipif(not TAHLAMUS_AVAILABLE, reason="Tahlamus not available")
def test_consciousness_metrics():
    """Test consciousness metrics extraction"""
    data_dir = Path(__file__).parent.parent / "data"
    bridge = create_tahlamus_bridge(data_dir=data_dir)

    prediction = bridge.process_request("Complex task requiring deep thought")

    consciousness = bridge.get_consciousness_state(prediction)

    assert isinstance(consciousness, dict), "Should return a dictionary"
    print(f"\n✓ Consciousness Metrics:")
    print(f"  - Integration: {consciousness.get('integration_level', 0):.3f}")
    print(f"  - Broadcast: {consciousness.get('broadcast_strength', 0):.3f}")
    print(f"  - Awareness: {consciousness.get('awareness_score', 0):.3f}")
    print(f"  - State: {consciousness.get('global_workspace_state', 'unknown')}")


@pytest.mark.skipif(not TAHLAMUS_AVAILABLE, reason="Tahlamus not available")
def test_semantic_coherence():
    """Test semantic coherence validation"""
    data_dir = Path(__file__).parent.parent / "data"
    bridge = create_tahlamus_bridge(data_dir=data_dir)

    prediction = bridge.process_request("Validate this response")

    coherence = bridge.check_semantic_coherence(prediction)

    assert isinstance(coherence, dict), "Should return a dictionary"
    print(f"\n✓ Semantic Coherence:")
    print(f"  - Coherence K: {coherence.get('coherence_K', 0):.3f}")
    print(f"  - Truth Stability: {coherence.get('truth_stability', 0):.3f}")
    print(f"  - Status: {coherence.get('semantic_status', 'unknown')}")


if __name__ == "__main__":
    print("=" * 60)
    print("Tahlamus Integration Test Suite")
    print("=" * 60)

    test_tahlamus_path_detection()
    test_tahlamus_bridge_creation()

    if TAHLAMUS_AVAILABLE:
        print("\n" + "=" * 60)
        print("Running Tahlamus-dependent tests...")
        print("=" * 60)

        test_tahlamus_prediction()
        test_memory_context_retrieval()
        test_learning_from_outcome()
        test_consciousness_metrics()
        test_semantic_coherence()

        print("\n" + "=" * 60)
        print("✓ All Tahlamus tests passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  Tahlamus not available - skipping dependent tests")
        print(f"   Clone Tahlamus to: {TAHLAMUS_PATH}")
        print("   From: https://github.com/Flissel/the_brain.git")
        print("=" * 60)
