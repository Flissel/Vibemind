import asyncio
import random
import json
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class Individual:
    """Individual in the evolutionary population"""
    genome: Dict[str, Any]
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutations: List[str] = field(default_factory=list)
    
    def mutate(self, mutation_rate: float = 0.1) -> 'Individual':
        """Create a mutated copy of this individual"""
        new_genome = json.loads(json.dumps(self.genome))  # Deep copy
        mutations = []
        
        def mutate_value(value, path=""):
            if isinstance(value, dict):
                for k, v in value.items():
                    value[k] = mutate_value(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    value[i] = mutate_value(v, f"{path}[{i}]")
            elif isinstance(value, (int, float)):
                if random.random() < mutation_rate:
                    # Gaussian mutation
                    mutation = np.random.normal(0, 0.1)
                    value = value * (1 + mutation)
                    mutations.append(f"{path}: {mutation:.3f}")
            elif isinstance(value, bool):
                if random.random() < mutation_rate:
                    value = not value
                    mutations.append(f"{path}: flipped")
            elif isinstance(value, str):
                if random.random() < mutation_rate:
                    # String mutations could involve small edits
                    mutations.append(f"{path}: modified")
            
            return value
        
        new_genome = mutate_value(new_genome)
        
        return Individual(
            genome=new_genome,
            generation=self.generation + 1,
            parent_ids=[str(id(self))],
            mutations=mutations
        )
    
    def crossover(self, other: 'Individual') -> 'Individual':
        """Create offspring through crossover"""
        new_genome = {}
        
        def crossover_values(v1, v2):
            if type(v1) != type(v2):
                return v1 if random.random() < 0.5 else v2
            
            if isinstance(v1, dict):
                result = {}
                all_keys = set(v1.keys()) | set(v2.keys())
                for k in all_keys:
                    if k in v1 and k in v2:
                        result[k] = crossover_values(v1[k], v2[k])
                    elif k in v1:
                        result[k] = v1[k]
                    else:
                        result[k] = v2[k]
                return result
            elif isinstance(v1, list):
                # Blend lists
                max_len = max(len(v1), len(v2))
                result = []
                for i in range(max_len):
                    if i < len(v1) and i < len(v2):
                        result.append(v1[i] if random.random() < 0.5 else v2[i])
                    elif i < len(v1):
                        result.append(v1[i])
                    else:
                        result.append(v2[i])
                return result
            elif isinstance(v1, (int, float)):
                # Arithmetic crossover
                alpha = random.random()
                return alpha * v1 + (1 - alpha) * v2
            else:
                # Random selection for other types
                return v1 if random.random() < 0.5 else v2
        
        new_genome = crossover_values(self.genome, other.genome)
        
        return Individual(
            genome=new_genome,
            generation=max(self.generation, other.generation) + 1,
            parent_ids=[str(id(self)), str(id(other))]
        )

class EvolutionaryLearner:
    """Evolutionary algorithm for self-improvement inspired by Sakana AI"""

    def __init__(
        self,
        population_size: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elite_size: int = 2,
        archive_path: Optional[Path] = None,
        tahlamus_bridge: Optional[Any] = None
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        self.archive_path = archive_path

        self.population: List[Individual] = []
        self.archive: List[Individual] = []  # Best individuals across all generations
        self.generation = 0
        self.fitness_function: Optional[Callable] = None

        # Tahlamus Meta-Learning integration
        self.tahlamus = tahlamus_bridge
        self.meta_learner = None
        self.last_best_fitness = 0.0  # Track improvement for meta-learning

        # Initialize Tahlamus Meta-Learning if available
        if self.tahlamus and hasattr(self.tahlamus, 'planner') and self.tahlamus.planner:
            try:
                from core.meta_learning import MetaLearner, MetaParameters
                initial_params = MetaParameters(
                    exploration_rate=mutation_rate,
                    memory_learning_rate=crossover_rate,
                    attention_focus_strength=elite_size / population_size
                )
                self.meta_learner = MetaLearner(initial_meta_params=initial_params)
                logger.info("Tahlamus Meta-Learning enabled for EvolutionaryLearner")
            except ImportError as e:
                logger.warning(f"Tahlamus Meta-Learning unavailable: {e}")
                self.meta_learner = None
    
    def initialize_population(self, base_genome: Dict[str, Any]):
        """Initialize population with variations of base genome"""
        self.population = []
        
        # Add the base individual
        self.population.append(Individual(genome=base_genome))
        
        # Create variations
        for _ in range(self.population_size - 1):
            # Start from base or random archive member
            if self.archive and random.random() < 0.3:
                parent = random.choice(self.archive)
            else:
                parent = self.population[0]
            
            # Create mutated individual
            mutated = parent.mutate(self.mutation_rate * 2)  # Higher initial mutation
            self.population.append(mutated)
        
        logger.info(f"Initialized population with {len(self.population)} individuals")
    
    async def evaluate_population(self, fitness_function: Callable):
        """Evaluate fitness of all individuals"""
        self.fitness_function = fitness_function

        # Evaluate fitness in parallel
        tasks = []
        for individual in self.population:
            task = asyncio.create_task(self._evaluate_individual(individual))
            tasks.append(task)

        fitnesses = await asyncio.gather(*tasks)

        for individual, fitness in zip(self.population, fitnesses):
            individual.fitness = fitness

        # Sort by fitness
        self.population.sort(key=lambda x: x.fitness, reverse=True)

        # Update archive with best individuals
        self._update_archive()

        logger.info(f"Generation {self.generation} - Best fitness: {self.population[0].fitness:.3f}")

        # Adapt meta-parameters if Tahlamus enabled
        if self.meta_learner:
            await self._adapt_parameters_from_tahlamus()
    
    async def _evaluate_individual(self, individual: Individual) -> float:
        """Evaluate a single individual"""
        try:
            if asyncio.iscoroutinefunction(self.fitness_function):
                fitness = await self.fitness_function(individual.genome)
            else:
                fitness = self.fitness_function(individual.genome)
            return float(fitness)
        except Exception as e:
            logger.error(f"Error evaluating individual: {e}")
            return 0.0
    
    def evolve_generation(self):
        """Create next generation through selection, crossover, and mutation"""
        new_population = []
        
        # Elite selection - keep best individuals
        for i in range(self.elite_size):
            if i < len(self.population):
                new_population.append(self.population[i])
        
        # Fill rest of population
        while len(new_population) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_select()
            
            if random.random() < self.crossover_rate:
                parent2 = self._tournament_select()
                offspring = parent1.crossover(parent2)
            else:
                offspring = Individual(
                    genome=json.loads(json.dumps(parent1.genome)),
                    generation=parent1.generation + 1,
                    parent_ids=[str(id(parent1))]
                )
            
            # Mutation
            if random.random() < self.mutation_rate:
                offspring = offspring.mutate(self.mutation_rate)
            
            new_population.append(offspring)
        
        self.population = new_population
        self.generation += 1
    
    def _tournament_select(self, tournament_size: int = 3) -> Individual:
        """Select individual using tournament selection"""
        tournament = random.sample(self.population, min(tournament_size, len(self.population)))
        return max(tournament, key=lambda x: x.fitness)
    
    def _update_archive(self):
        """Update archive with best individuals"""
        # Add best individual from current generation
        if self.population:
            best = self.population[0]
            
            # Check if it's better than worst in archive or archive not full
            if len(self.archive) < 50:  # Max archive size
                self.archive.append(best)
            else:
                worst_idx = min(range(len(self.archive)), 
                              key=lambda i: self.archive[i].fitness)
                if best.fitness > self.archive[worst_idx].fitness:
                    self.archive[worst_idx] = best
            
            # Sort archive
            self.archive.sort(key=lambda x: x.fitness, reverse=True)
            
            # Save archive if path provided
            if self.archive_path:
                self._save_archive()
    
    def _save_archive(self):
        """Save archive to disk"""
        try:
            archive_data = []
            for individual in self.archive:
                archive_data.append({
                    'genome': individual.genome,
                    'fitness': individual.fitness,
                    'generation': individual.generation,
                    'mutations': individual.mutations
                })
            
            with open(self.archive_path, 'w') as f:
                json.dump(archive_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save archive: {e}")
    
    def load_archive(self):
        """Load archive from disk"""
        if self.archive_path and self.archive_path.exists():
            try:
                with open(self.archive_path, 'r') as f:
                    archive_data = json.load(f)
                
                self.archive = []
                for data in archive_data:
                    individual = Individual(
                        genome=data['genome'],
                        fitness=data['fitness'],
                        generation=data.get('generation', 0),
                        mutations=data.get('mutations', [])
                    )
                    self.archive.append(individual)
                
                logger.info(f"Loaded {len(self.archive)} individuals from archive")
            except Exception as e:
                logger.error(f"Failed to load archive: {e}")
    
    def get_best_genome(self) -> Dict[str, Any]:
        """Get the best genome found so far"""
        if self.archive:
            return self.archive[0].genome
        elif self.population:
            return self.population[0].genome
        else:
            return {}
    
    def get_best_fitness(self) -> float:
        """Get the fitness of the best individual"""
        if self.archive and self.archive[0].fitness > 0:
            return self.archive[0].fitness
        elif self.population:
            return self.population[0].fitness
        else:
            return 0.0

    async def _adapt_parameters_from_tahlamus(self):
        """Adapt genetic algorithm parameters using Tahlamus Meta-Learning"""
        if not self.meta_learner or not self.population:
            return

        # Compute performance metrics
        best_fitness = self.population[0].fitness
        fitness_improvement = best_fitness - self.last_best_fitness

        # Determine outcome
        outcome = 'success' if fitness_improvement > 0 else 'failure'

        # Compute prediction error (normalized fitness delta)
        # High error = unstable fitness, low error = stable/improving
        prediction_error = abs(fitness_improvement) / (abs(best_fitness) + 1e-6)
        prediction_error = min(prediction_error, 1.0)  # Clip to [0, 1]

        # Compute confidence (normalized fitness)
        # Assume max fitness is around 100.0 for normalization
        confidence = min(best_fitness / 100.0, 1.0)

        # Adapt meta-parameters
        updated_params = self.meta_learner.adapt_meta_parameters(
            outcome=outcome,
            prediction_error=prediction_error,
            confidence=confidence,
            attention_entropy=None  # Not applicable for GA
        )

        # Apply adapted parameters to genetic algorithm
        old_mutation = self.mutation_rate
        old_crossover = self.crossover_rate
        old_elite = self.elite_size

        self.mutation_rate = updated_params.exploration_rate
        self.crossover_rate = updated_params.memory_learning_rate

        # Update elite size based on attention focus
        new_elite_size = max(1, int(updated_params.attention_focus_strength * self.population_size))
        self.elite_size = min(new_elite_size, self.population_size // 2)

        # Log adaptation if parameters changed significantly
        if (abs(self.mutation_rate - old_mutation) > 0.01 or
                abs(self.crossover_rate - old_crossover) > 0.01 or
                self.elite_size != old_elite):
            logger.info(
                f"Tahlamus adapted GA params (gen {self.generation}): "
                f"mutation={old_mutation:.3f}→{self.mutation_rate:.3f}, "
                f"crossover={old_crossover:.3f}→{self.crossover_rate:.3f}, "
                f"elite={old_elite}→{self.elite_size}, "
                f"fitness_delta={fitness_improvement:+.3f}"
            )

        # Update last fitness for next iteration
        self.last_best_fitness = best_fitness