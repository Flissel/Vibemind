"""
Evolution triggers for self-improvement based on task failures
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class EvolutionTrigger:
    """Monitors task failures and triggers evolutionary improvements"""
    
    def __init__(self, assistant):
        self.assistant = assistant
        self.failure_patterns = []
        self.evolution_threshold = 3  # Failures before triggering evolution
        self.current_failures = {}
        
    async def on_task_failure(self, task_type: str, context: Dict[str, Any], error: str):
        """Called when a task fails"""
        
        # Record failure
        failure = {
            'task_type': task_type,
            'context': context,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        # Track failure patterns
        if task_type not in self.current_failures:
            self.current_failures[task_type] = []
        
        self.current_failures[task_type].append(failure)
        
        # Check if we should trigger evolution
        if len(self.current_failures[task_type]) >= self.evolution_threshold:
            logger.info(f"Triggering evolution for task type: {task_type}")
            await self._trigger_evolution(task_type)
    
    async def _trigger_evolution(self, task_type: str):
        """Trigger evolutionary improvement for specific task type"""
        
        # Define the problem space
        problem_definition = {
            'task_type': task_type,
            'failures': self.current_failures[task_type],
            'goal': f"Evolve capability to handle {task_type} tasks"
        }
        
        # Create fitness function for this specific problem
        async def task_fitness(genome: Dict[str, Any]) -> float:
            """Evaluate how well a genome solves the task"""
            fitness = 0.0
            
            # Test against recorded failures
            for failure in self.current_failures[task_type][-5:]:  # Last 5 failures
                try:
                    # Simulate the task with new genome
                    success = await self._test_genome_on_task(genome, failure)
                    if success:
                        fitness += 20.0
                except Exception as e:
                    logger.debug(f"Genome test failed: {e}")
                    fitness -= 10.0
            
            return max(0.0, fitness)
        
        # Start evolutionary process
        if self.assistant.evolutionary_learner:
            # Create initial population with behavior variations
            initial_genome = self._create_behavior_genome(task_type)
            self.assistant.evolutionary_learner.initialize_population(initial_genome)
            
            # Run evolution
            for generation in range(5):  # Quick evolution cycles
                await self.assistant.evolutionary_learner.evaluate_population(task_fitness)
                self.assistant.evolutionary_learner.evolve_generation()
            
            # Apply best evolved behavior
            best_genome = self.assistant.evolutionary_learner.get_best_genome()
            await self._apply_evolved_behavior(task_type, best_genome)
            
            # Clear failure history for this task
            self.current_failures[task_type] = []
    
    def _create_behavior_genome(self, task_type: str) -> Dict[str, Any]:
        """Create genome that includes behaviors, not just parameters"""
        
        if task_type == "document_summarization":
            return {
                'approach': 'direct',  # direct, exploratory, pattern-based
                'file_reading_method': 'cat',  # cat, read, custom
                'path_handling': 'absolute',  # absolute, relative, smart
                'content_processing': 'full',  # full, chunked, selective
                'summary_style': 'concise',  # concise, detailed, bullet
                'learning_from_errors': True,
                'exploration_rate': 0.3,
                'commands_to_try': ['cat', 'ls', 'find', 'read'],
                'path_patterns': ['C:\\', '/mnt/c/', '~/', './'],
                'error_recovery': 'retry_variations'  # retry_variations, ask_user, fallback
            }
        elif task_type == "command_execution":
            return {
                'command_discovery': True,
                'syntax_learning': True,
                'error_interpretation': True,
                'command_chaining': False,
                'available_commands': []  # Will be discovered
            }
        else:
            return {
                'general_approach': 'exploratory',
                'learning_rate': 0.1,
                'creativity': 0.5,
                'persistence': 0.8
            }
    
    async def _test_genome_on_task(self, genome: Dict[str, Any], failure: Dict[str, Any]) -> bool:
        """Test if a genome would handle a failed task successfully"""
        
        # Simulate task execution with genome behaviors
        task_type = failure['task_type']
        
        if task_type == "document_summarization":
            # Check if genome would handle the file path correctly
            if genome.get('path_handling') == 'smart':
                # Would try multiple path formats
                return True
            elif genome.get('exploration_rate', 0) > 0.5:
                # High exploration might discover solution
                return True
        
        return False
    
    async def _apply_evolved_behavior(self, task_type: str, genome: Dict[str, Any]):
        """Apply the evolved behavior to the assistant"""
        
        logger.info(f"Applying evolved behavior for {task_type}: {genome}")
        
        # Store evolved behavior in assistant's memory
        evolution_memory = {
            'type': 'evolved_capability',
            'task_type': task_type,
            'genome': genome,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to pattern memory
        await self.assistant.memory_manager.detect_pattern(
            'evolved_behavior',
            evolution_memory
        )
        
        # Update assistant's approach based on evolved genome
        if hasattr(self.assistant, 'behavior_genome'):
            self.assistant.behavior_genome[task_type] = genome
        else:
            self.assistant.behavior_genome = {task_type: genome}
    
    def analyze_user_feedback(self, feedback: str, context: Dict[str, Any]) -> Optional[str]:
        """Analyze user feedback for improvement signals"""
        
        negative_signals = ['not true', 'wrong', 'incorrect', 'no', 'failed', "that's not", "this is not"]
        positive_signals = ['yes', 'correct', 'good', 'right', 'exactly', 'perfect']
        
        feedback_lower = feedback.lower()
        
        # Check for negative feedback
        for signal in negative_signals:
            if signal in feedback_lower:
                return 'negative'
        
        # Check for positive feedback
        for signal in positive_signals:
            if signal in feedback_lower:
                return 'positive'
        
        return None