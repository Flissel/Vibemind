"""
TahalamusBridge - Integration layer between Sakana and Tahlamus

This module provides a bridge to Tahlamus's cognitive architecture,
allowing Sakana to use all 13 cognitive features:

1. Memory Systems - Working, episodic, long-term memory
2. Predictive Coding - Error-driven learning, curiosity signals
3. Attention Mechanisms - 6 modality gates (vision, audio, touch, taste, vestibular, threat)
4. Meta-Learning - Adaptive learning rate, exploration rate
5. Neuromodulation - Dopamine, serotonin, learning rate boost
6. Temporal Memory - Time-based patterns (hour, day, week)
7. Active Inference - Bayesian hypothesis generation
8. Compositional Reasoning - Task decomposition
9. Tool Creation - Generate new tools
10. Consciousness Metrics - Integration, broadcast, awareness
11. Infinite Chat - Persistent memory via Supermemory
12. Semantic Coherence - Truth validation
13. CTM Async - Continuous thinking models

Usage:
    bridge = TahalamusBridge(data_dir=Path("data"))
    prediction = bridge.process_request("Open Excel")
    print(prediction.actionable_decision.primary_action)
"""

from pathlib import Path
from typing import Optional, Dict, Any
import logging

from . import TAHLAMUS_AVAILABLE

if TAHLAMUS_AVAILABLE:
    try:
        from production.production_planner import ProductionPlanner
        from core.hierarchical_planner import HierarchicalPrediction
    except ImportError as e:
        logging.warning(f"Failed to import Tahlamus modules: {e}")
        TAHLAMUS_AVAILABLE = False


class TahalamusBridge:
    """
    Bridge between Sakana and Tahlamus cognitive systems

    This class provides a high-level interface to Tahlamus's cognitive
    architecture, making it easy for Sakana to leverage all 13 features.
    """

    def __init__(
        self,
        data_dir: Path,
        enable_continuous_learning: bool = True,
        enable_semantic_coherence: bool = True,
        user_id: str = "sakana_main",
        openrouter_api_key: Optional[str] = None
    ):
        """
        Initialize Tahlamus bridge

        Args:
            data_dir: Path to data directory for session logs
            enable_continuous_learning: Whether to learn from feedback
            enable_semantic_coherence: Whether to validate semantic coherence
            user_id: User ID for memory isolation (enables Infinite Chat)
            openrouter_api_key: Optional OpenRouter API key for LLM features
        """
        self.data_dir = data_dir
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)

        if not TAHLAMUS_AVAILABLE:
            self.logger.warning(
                "Tahlamus not available. Install from: "
                "https://github.com/Flissel/the_brain"
            )
            self.planner = None
            return

        # Create Tahlamus session directory
        tahlamus_dir = data_dir / "tahlamus_sessions"
        tahlamus_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ProductionPlanner with all 13 features
        try:
            self.planner = ProductionPlanner(
                session_log_dir=str(tahlamus_dir),
                enable_continuous_learning=enable_continuous_learning,
                enable_semantic_coherence=enable_semantic_coherence,
                user_id=user_id,
                openrouter_api_key=openrouter_api_key
            )
            self.logger.info(
                f"Tahlamus initialized with 13 cognitive features "
                f"(user_id={user_id})"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Tahlamus: {e}")
            self.planner = None

    def is_available(self) -> bool:
        """Check if Tahlamus is available and initialized"""
        return self.planner is not None

    def process_request(self, user_input: str) -> Optional['HierarchicalPrediction']:
        """
        Process user request through Tahlamus cognitive layers

        This runs the input through all 3 hierarchical layers:
        - Layer 1: TaskFeatureRouter (Memory, Predictive Coding, Attention)
        - Layer 2: ConversationPathPlanner (Temporal, Meta-Learning)
        - Layer 3: DecisionRouter (Neuromodulation, Active Inference, Compositional, Tools)

        Plus: Consciousness Metrics, Semantic Coherence, CTM Async

        Args:
            user_input: User's request/command

        Returns:
            HierarchicalPrediction with all cognitive features,
            or None if Tahlamus not available
        """
        if not self.is_available():
            self.logger.warning("Tahlamus not available, skipping cognitive processing")
            return None

        try:
            prediction = self.planner.predict(user_input)

            self.logger.info(
                f"Tahlamus prediction: {prediction.actionable_decision.primary_action} "
                f"(confidence={prediction.actionable_decision.confidence:.2f})"
            )

            return prediction

        except Exception as e:
            self.logger.error(f"Tahlamus prediction failed: {e}")
            return None

    def get_memory_context(self, task: str) -> Dict[str, Any]:
        """
        Get memory context for a task

        Returns:
            dict with working_memory, episodic_memories, and memory sizes
        """
        if not self.is_available():
            return {}

        try:
            prediction = self.planner.predict(task)
            return prediction.memory_context or {}
        except Exception as e:
            self.logger.error(f"Failed to get memory context: {e}")
            return {}

    def learn_from_outcome(
        self,
        task: str,
        predicted_action: str,
        actual_action: str,
        success: bool,
        execution_time_ms: Optional[float] = None
    ):
        """
        Update Tahlamus from execution outcome

        This enables continuous learning - Tahlamus adapts its
        cognitive parameters based on feedback.

        Args:
            task: The original task/request
            predicted_action: What Tahlamus predicted
            actual_action: What actually happened
            success: Whether the outcome was successful
            execution_time_ms: Optional execution time for performance tracking
        """
        if not self.is_available():
            return

        try:
            self.planner.give_feedback(
                task=task,
                predicted_action=predicted_action,
                actual_action=actual_action,
                success=success,
                execution_time_ms=execution_time_ms
            )

            self.logger.info(
                f"Tahlamus learned from outcome: {task[:50]}... "
                f"(success={success})"
            )

        except Exception as e:
            self.logger.error(f"Failed to give feedback to Tahlamus: {e}")

    def get_consciousness_state(self, prediction: 'HierarchicalPrediction') -> Dict[str, Any]:
        """
        Get consciousness metrics from a prediction

        Returns:
            dict with integration_level, broadcast_strength, awareness_score,
            and global_workspace_state
        """
        if prediction and prediction.cognitive_state:
            return {
                "integration_level": prediction.cognitive_state.integration_level,
                "broadcast_strength": prediction.cognitive_state.broadcast_strength,
                "awareness_score": prediction.cognitive_state.awareness_score,
                "global_workspace_state": prediction.cognitive_state.global_workspace_state
            }
        return {}

    def check_semantic_coherence(
        self,
        prediction: 'HierarchicalPrediction'
    ) -> Dict[str, Any]:
        """
        Check semantic coherence of a prediction

        Returns:
            dict with coherence_K, truth_stability, semantic_status
        """
        if prediction and hasattr(prediction, 'semantic_coherence'):
            return {
                "coherence_K": prediction.semantic_coherence.get("coherence_K", 0.0),
                "truth_stability": prediction.semantic_coherence.get("truth_stability", 0.0),
                "semantic_status": prediction.semantic_coherence.get("semantic_status", "UNKNOWN")
            }
        return {}


# Convenience function for quick access
def create_tahlamus_bridge(
    data_dir: Path,
    **kwargs
) -> TahalamusBridge:
    """
    Factory function to create a TahalamusBridge instance

    Args:
        data_dir: Path to data directory
        **kwargs: Additional arguments to pass to TahalamusBridge

    Returns:
        TahalamusBridge instance
    """
    return TahalamusBridge(data_dir=data_dir, **kwargs)
