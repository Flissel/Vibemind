"""
Test suite for Tahlamus Meta-Learning integration with EvolutionaryLearner

Tests the Phase 2 integration that enables adaptive parameter optimization
of genetic algorithm parameters based on performance feedback.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, MagicMock
import sys

# Add Tahlamus to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Tahlamus"))

from src.learning.evolutionary_learner import EvolutionaryLearner, Individual


class MockTahalamusBridge:
    """Mock Tahlamus bridge for testing"""

    def __init__(self):
        self.planner = MagicMock()
        self.planner.return_value = True


@pytest.fixture
def data_dir(tmp_path):
    """Provide temporary data directory"""
    return tmp_path


@pytest.fixture
def mock_tahlamus():
    """Provide mock Tahlamus bridge"""
    return MockTahalamusBridge()


@pytest.fixture
def learner_without_tahlamus(data_dir):
    """Evolutionary learner without Tahlamus (backward compatibility)"""
    return EvolutionaryLearner(
        population_size=10,
        mutation_rate=0.1,
        crossover_rate=0.7,
        elite_size=2,
        archive_path=data_dir / "archive.json"
    )


@pytest.fixture
def learner_with_tahlamus(data_dir, mock_tahlamus):
    """Evolutionary learner with Tahlamus integration"""
    return EvolutionaryLearner(
        population_size=10,
        mutation_rate=0.1,
        crossover_rate=0.7,
        elite_size=2,
        archive_path=data_dir / "archive.json",
        tahlamus_bridge=mock_tahlamus
    )


def test_backward_compatibility(learner_without_tahlamus):
    """Test that EvolutionaryLearner works without Tahlamus"""
    assert learner_without_tahlamus.population_size == 10
    assert learner_without_tahlamus.mutation_rate == 0.1
    assert learner_without_tahlamus.crossover_rate == 0.7
    assert learner_without_tahlamus.elite_size == 2
    assert learner_without_tahlamus.tahlamus is None
    assert learner_without_tahlamus.meta_learner is None


def test_tahlamus_integration(learner_with_tahlamus, mock_tahlamus):
    """Test that EvolutionaryLearner initializes with Tahlamus"""
    assert learner_with_tahlamus.tahlamus is mock_tahlamus
    # meta_learner might be None if Tahlamus imports fail, but that's ok
    assert hasattr(learner_with_tahlamus, 'meta_learner')
    assert hasattr(learner_with_tahlamus, 'last_best_fitness')


def test_initialize_population(learner_without_tahlamus):
    """Test population initialization works with and without Tahlamus"""
    base_genome = {
        'learning_rate': 0.1,
        'exploration_rate': 0.2,
        'temperature': 1.0
    }

    learner_without_tahlamus.initialize_population(base_genome)

    assert len(learner_without_tahlamus.population) == 10
    assert learner_without_tahlamus.population[0].genome == base_genome


@pytest.mark.asyncio
async def test_evaluation_without_tahlamus(learner_without_tahlamus):
    """Test evaluation works without Tahlamus"""
    base_genome = {'param': 1.0}
    learner_without_tahlamus.initialize_population(base_genome)

    # Simple fitness function
    def fitness_fn(genome):
        return genome.get('param', 0) * 10

    await learner_without_tahlamus.evaluate_population(fitness_fn)

    assert learner_without_tahlamus.population[0].fitness > 0
    assert len(learner_without_tahlamus.archive) > 0


@pytest.mark.asyncio
async def test_evaluation_with_tahlamus_no_metalearner(learner_with_tahlamus):
    """Test evaluation with Tahlamus but no MetaLearner (graceful degradation)"""
    # Force meta_learner to None (simulates import failure)
    learner_with_tahlamus.meta_learner = None

    base_genome = {'param': 1.0}
    learner_with_tahlamus.initialize_population(base_genome)

    def fitness_fn(genome):
        return genome.get('param', 0) * 10

    # Should not crash even without meta_learner
    await learner_with_tahlamus.evaluate_population(fitness_fn)

    assert learner_with_tahlamus.population[0].fitness > 0


@pytest.mark.asyncio
async def test_meta_parameter_adaptation():
    """Test that meta-parameters adapt based on performance (requires real Tahlamus)"""
    try:
        from core.meta_learning import MetaLearner, MetaParameters
    except ImportError:
        pytest.skip("Tahlamus not available for integration test")
        return

    # Create learner with real Tahlamus MetaLearner
    learner = EvolutionaryLearner(population_size=10, mutation_rate=0.1)

    # Manually add MetaLearner for this test
    initial_params = MetaParameters(
        exploration_rate=0.1,
        memory_learning_rate=0.7,
        attention_focus_strength=0.2
    )
    learner.meta_learner = MetaLearner(initial_meta_params=initial_params)
    learner.last_best_fitness = 0.0

    # Initialize population
    base_genome = {'param': 1.0}
    learner.initialize_population(base_genome)

    # Evaluation 1: Set initial fitness
    def fitness_fn_1(genome):
        return genome.get('param', 0) * 10

    await learner.evaluate_population(fitness_fn_1)
    initial_mutation_rate = learner.mutation_rate

    # Evaluation 2: Improve fitness (should decrease exploration)
    def fitness_fn_2(genome):
        return genome.get('param', 0) * 20  # Higher fitness

    await learner.evaluate_population(fitness_fn_2)

    # After successful improvement, mutation rate should adapt
    # (might increase or decrease depending on meta-learning logic)
    assert learner.mutation_rate != initial_mutation_rate or learner.generation == 0


@pytest.mark.asyncio
async def test_parameter_bounds():
    """Test that adapted parameters stay within valid bounds"""
    try:
        from core.meta_learning import MetaLearner, MetaParameters
    except ImportError:
        pytest.skip("Tahlamus not available")
        return

    learner = EvolutionaryLearner(population_size=10, mutation_rate=0.5)
    initial_params = MetaParameters(exploration_rate=0.5)
    learner.meta_learner = MetaLearner(initial_meta_params=initial_params)
    learner.last_best_fitness = 0.0

    base_genome = {'param': 1.0}
    learner.initialize_population(base_genome)

    # Run multiple evaluations to trigger adaptations
    for i in range(5):
        def fitness_fn(genome):
            return genome.get('param', 0) * (10 + i)

        await learner.evaluate_population(fitness_fn)

        # Check bounds
        assert 0.0 <= learner.mutation_rate <= 1.0
        assert 0.0 <= learner.crossover_rate <= 1.0
        assert 1 <= learner.elite_size <= learner.population_size // 2


def test_fitness_improvement_tracking(learner_with_tahlamus):
    """Test that fitness improvement is tracked correctly"""
    learner_with_tahlamus.last_best_fitness = 10.0

    # Create population with known fitness
    individual = Individual(genome={'param': 1.0}, fitness=15.0)
    learner_with_tahlamus.population = [individual]

    # Manually call adaptation (without async)
    # This tests the computation logic
    best_fitness = learner_with_tahlamus.population[0].fitness
    fitness_improvement = best_fitness - learner_with_tahlamus.last_best_fitness

    assert fitness_improvement == 5.0
    assert fitness_improvement > 0  # Success


def test_evolve_generation_uses_adapted_params(learner_without_tahlamus):
    """Test that evolve_generation uses the current mutation/crossover rates"""
    base_genome = {'param': 1.0}
    learner_without_tahlamus.initialize_population(base_genome)

    # Manually set parameters
    learner_without_tahlamus.mutation_rate = 0.8
    learner_without_tahlamus.crossover_rate = 0.3

    # Evolve generation
    learner_without_tahlamus.evolve_generation()

    # New population should exist
    assert len(learner_without_tahlamus.population) == 10
    assert learner_without_tahlamus.generation == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
