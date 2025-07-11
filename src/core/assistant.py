import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import logging

from .config import Config
from .llm_interface import LLMFactory
from ..memory import MemoryManager, Memory, MemoryType, PatternDetector
from ..learning import EvolutionaryLearner, SelfModifier, ReinforcementLearner
from ..execution import SandboxExecutor
from ..plugins import PluginManager

logger = logging.getLogger(__name__)

class SakanaAssistant:
    """Main assistant class with self-learning capabilities"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Core components
        self.llm = None
        self.memory_manager = None
        self.pattern_detector = None
        self.evolutionary_learner = None
        self.self_modifier = None
        self.sandbox_executor = None
        self.plugin_manager = None
        
        # State
        self.is_initialized = False
        self.conversation_history = []
        self.current_context = {}
        self.learning_enabled = True
        
        # Performance tracking
        self.metrics = {
            'requests_handled': 0,
            'successful_completions': 0,
            'errors': 0,
            'average_response_time': 0.0,
            'patterns_learned': 0,
            'self_improvements': 0
        }
    
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Sakana Desktop Assistant...")
        
        # Initialize LLM
        self.llm = LLMFactory.create(self.config)
        
        # Initialize memory system
        self.memory_manager = MemoryManager(
            db_path=self.config.memory_db_path,
            llm_interface=self.llm
        )
        await self.memory_manager.initialize()
        
        # Initialize pattern detector
        self.pattern_detector = PatternDetector(self.memory_manager)
        
        # Initialize learning systems
        self.evolutionary_learner = EvolutionaryLearner(
            population_size=self.config.population_size,
            mutation_rate=self.config.mutation_rate,
            archive_path=self.config.data_dir / "evolution_archive.json"
        )
        self.evolutionary_learner.load_archive()
        
        self.self_modifier = SelfModifier(
            sandbox_enabled=self.config.sandbox_enabled,
            modifications_dir=self.config.data_dir / "modifications"
        )
        
        # Initialize execution sandbox
        if self.config.sandbox_enabled:
            self.sandbox_executor = SandboxExecutor(
                max_execution_time=self.config.max_execution_time
            )
            await self.sandbox_executor.initialize()
        
        # Initialize plugin system
        self.plugin_manager = PluginManager(self.config.plugins_dir)
        await self.plugin_manager.load_plugins()
        
        # Load user preferences and patterns
        await self._load_user_profile()
        
        self.is_initialized = True
        logger.info("Assistant initialized successfully")
    
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process a user request with learning and adaptation"""
        
        start_time = datetime.now()
        self.metrics['requests_handled'] += 1
        
        try:
            # Store in short-term memory
            input_memory = Memory(
                type=MemoryType.SHORT_TERM,
                content=user_input,
                context={'type': 'user_input', 'timestamp': start_time.isoformat()}
            )
            await self.memory_manager.store_memory(input_memory)
            
            # Detect patterns in user behavior
            await self._detect_user_patterns(user_input)
            
            # Retrieve relevant memories
            relevant_memories = await self.memory_manager.retrieve_memories(
                query=user_input,
                limit=10
            )
            
            # Build context
            context = self._build_context(user_input, relevant_memories)
            
            # Check for plugin commands
            plugin_response = await self.plugin_manager.handle_command(user_input, context)
            if plugin_response:
                response = plugin_response
            else:
                # Generate response using LLM
                response = await self._generate_response(user_input, context)
            
            # Execute any requested actions
            if self._contains_code_request(response):
                execution_result = await self._execute_code(response)
                response = self._merge_execution_result(response, execution_result)
            
            # Store response in memory
            response_memory = Memory(
                type=MemoryType.SHORT_TERM,
                content=response['content'],
                context={
                    'type': 'assistant_response',
                    'user_input': user_input,
                    'timestamp': datetime.now().isoformat()
                }
            )
            await self.memory_manager.store_memory(response_memory)
            
            # Learn from interaction
            if self.learning_enabled:
                await self._learn_from_interaction(user_input, response)
            
            # Update metrics
            self.metrics['successful_completions'] += 1
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_avg_response_time(response_time)
            
            return {
                'success': True,
                'response': response,
                'response_time': response_time,
                'memories_used': len(relevant_memories)
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            self.metrics['errors'] += 1
            
            return {
                'success': False,
                'error': str(e),
                'response': {
                    'content': "I encountered an error processing your request. Let me try a different approach.",
                    'type': 'error'
                }
            }
    
    async def _detect_user_patterns(self, user_input: str):
        """Detect patterns in user behavior"""
        
        # Time-based patterns
        current_hour = datetime.now().hour
        await self.memory_manager.detect_pattern(
            'time_preference',
            {'hour': current_hour, 'input_type': self._classify_input(user_input)}
        )
        
        # Command patterns
        if any(keyword in user_input.lower() for keyword in ['create', 'make', 'build']):
            await self.memory_manager.detect_pattern(
                'command_type',
                {'type': 'creation', 'keywords': self._extract_keywords(user_input)}
            )
        
        # Topic patterns
        topics = self._extract_topics(user_input)
        for topic in topics:
            await self.memory_manager.detect_pattern(
                'topic_interest',
                {'topic': topic}
            )
    
    async def _generate_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using LLM with context"""
        
        # Build prompt with context
        prompt = self._build_prompt(user_input, context)
        
        # Generate response
        response_text = await self.llm.generate(prompt)
        
        # Parse response for structured data
        response_data = self._parse_response(response_text)
        
        return {
            'content': response_data.get('content', response_text),
            'type': response_data.get('type', 'text'),
            'actions': response_data.get('actions', []),
            'metadata': response_data.get('metadata', {})
        }
    
    async def _execute_code(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code in sandbox if requested"""
        
        if not self.sandbox_executor:
            return {'success': False, 'error': 'Sandbox not enabled'}
        
        code = self._extract_code_from_response(response)
        if not code:
            return {'success': False, 'error': 'No code found'}
        
        # Execute in sandbox
        result = await self.sandbox_executor.execute(code)
        
        return result
    
    async def _learn_from_interaction(self, user_input: str, response: Dict[str, Any]):
        """Learn from the interaction to improve future responses"""
        
        # Update conversation patterns
        self.conversation_history.append({
            'user': user_input,
            'assistant': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Evolutionary learning - improve response generation
        if len(self.conversation_history) % 10 == 0:  # Every 10 interactions
            await self._run_evolutionary_improvement()
        
        # Pattern-based learning
        success_indicators = ['thank', 'perfect', 'great', 'exactly']
        if any(indicator in user_input.lower() for indicator in success_indicators):
            # Positive reinforcement
            await self.memory_manager.detect_pattern(
                'successful_response',
                {'response_type': response['type'], 'context': self.current_context}
            )
    
    async def _run_evolutionary_improvement(self):
        """Run evolutionary algorithm to improve assistant behavior"""
        
        # Define fitness function based on user satisfaction
        async def fitness_function(genome: Dict[str, Any]) -> float:
            # Evaluate based on response time, success rate, etc.
            fitness = 0.0
            
            # Factor in success rate
            if self.metrics['requests_handled'] > 0:
                success_rate = self.metrics['successful_completions'] / self.metrics['requests_handled']
                fitness += success_rate * 50
            
            # Factor in response time (lower is better)
            if self.metrics['average_response_time'] > 0:
                fitness += 10 / self.metrics['average_response_time']
            
            # Factor in learning rate
            fitness += self.metrics['patterns_learned'] * 2
            
            return fitness
        
        # Initialize population with current configuration
        current_genome = {
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'learning_rate': self.config.learning_rate,
            'pattern_threshold': 0.7
        }
        
        self.evolutionary_learner.initialize_population(current_genome)
        
        # Run evolution for a few generations
        for _ in range(5):
            await self.evolutionary_learner.evaluate_population(fitness_function)
            self.evolutionary_learner.evolve_generation()
        
        # Apply best genome
        best_genome = self.evolutionary_learner.get_best_genome()
        self._apply_genome(best_genome)
        
        self.metrics['self_improvements'] += 1
        logger.info(f"Completed evolutionary improvement cycle {self.metrics['self_improvements']}")
    
    async def _propose_self_improvement(self):
        """Propose and test self-modifications"""
        
        # Example: Improve response generation
        modification = await self.self_modifier.propose_modification(
            target_function=self._generate_response,
            improvement_prompt="Improve response generation to be more concise and relevant",
            llm_interface=self.llm
        )
        
        if modification['success']:
            # Test the modification
            test_cases = [
                {
                    'inputs': {
                        'user_input': "What's the weather?",
                        'context': {}
                    },
                    'expected': {'type': 'text'}
                }
            ]
            
            test_result = await self.self_modifier.test_modification(
                modification,
                test_cases
            )
            
            if test_result['success']:
                self.self_modifier.apply_modification(modification)
                logger.info("Applied self-improvement modification")
    
    def _build_context(self, user_input: str, memories: List[Memory]) -> Dict[str, Any]:
        """Build context from memories and current state"""
        
        context = {
            'user_input': user_input,
            'timestamp': datetime.now().isoformat(),
            'conversation_history': self.conversation_history[-5:],  # Last 5 exchanges
            'relevant_memories': [
                {
                    'content': m.content,
                    'context': m.context,
                    'importance': m.importance_score
                }
                for m in memories
            ],
            'user_patterns': [],
            'current_context': self.current_context
        }
        
        return context
    
    def _build_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Build prompt for LLM with context"""
        
        prompt_parts = [
            "You are Sakana, an intelligent desktop assistant with self-learning capabilities.",
            f"Current time: {context['timestamp']}",
            ""
        ]
        
        if context['relevant_memories']:
            prompt_parts.append("Relevant information from memory:")
            for mem in context['relevant_memories'][:3]:
                prompt_parts.append(f"- {mem['content']}")
            prompt_parts.append("")
        
        if context['conversation_history']:
            prompt_parts.append("Recent conversation:")
            for exchange in context['conversation_history'][-2:]:
                prompt_parts.append(f"User: {exchange['user']}")
                prompt_parts.append(f"Assistant: {exchange['assistant']['content'][:100]}...")
            prompt_parts.append("")
        
        prompt_parts.append(f"User request: {user_input}")
        prompt_parts.append("")
        prompt_parts.append("Provide a helpful, concise response. If code is needed, include it in ```python blocks.")
        
        return "\n".join(prompt_parts)
    
    def _apply_genome(self, genome: Dict[str, Any]):
        """Apply evolved parameters"""
        
        if 'temperature' in genome:
            self.config.temperature = genome['temperature']
        if 'max_tokens' in genome:
            self.config.max_tokens = genome['max_tokens']
        if 'learning_rate' in genome:
            self.config.learning_rate = genome['learning_rate']
    
    def _update_avg_response_time(self, new_time: float):
        """Update average response time"""
        
        current_avg = self.metrics['average_response_time']
        count = self.metrics['successful_completions']
        
        self.metrics['average_response_time'] = (
            (current_avg * (count - 1) + new_time) / count
        )
    
    async def _load_user_profile(self):
        """Load user preferences and patterns from memory"""
        
        patterns = await self.memory_manager.get_patterns(min_confidence=0.7)
        
        for pattern in patterns:
            if pattern['pattern_type'] == 'time_preference':
                # Adjust behavior based on time preferences
                pass
            elif pattern['pattern_type'] == 'topic_interest':
                # Prioritize certain topics
                pass
        
        self.metrics['patterns_learned'] = len(patterns)
    
    # Utility methods
    def _classify_input(self, text: str) -> str:
        """Classify input type"""
        if any(word in text.lower() for word in ['?', 'what', 'how', 'why']):
            return 'question'
        elif any(word in text.lower() for word in ['create', 'make', 'build']):
            return 'command'
        else:
            return 'statement'
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction - could be improved with NLP
        words = text.lower().split()
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        return [w for w in words if w not in stopwords and len(w) > 3]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text"""
        # Simplified topic extraction
        keywords = self._extract_keywords(text)
        return keywords[:3]  # Top 3 keywords as topics
    
    def _contains_code_request(self, response: Dict[str, Any]) -> bool:
        """Check if response contains code to execute"""
        return 'actions' in response and any(
            action.get('type') == 'execute_code' 
            for action in response['actions']
        )
    
    def _extract_code_from_response(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract code from response"""
        content = response.get('content', '')
        
        # Look for code blocks
        if '```python' in content:
            start = content.find('```python') + 9
            end = content.find('```', start)
            return content[start:end].strip()
        
        return None
    
    def _merge_execution_result(self, response: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Merge execution result into response"""
        
        if execution_result['success']:
            response['content'] += f"\n\nExecution result:\n{execution_result['output']}"
        else:
            response['content'] += f"\n\nExecution failed:\n{execution_result['error']}"
        
        response['execution_result'] = execution_result
        
        return response
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response for structured data"""
        
        # Try to extract JSON if present
        if '{' in response_text and '}' in response_text:
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                return json.loads(json_str)
            except:
                pass
        
        # Default response structure
        return {
            'content': response_text,
            'type': 'text'
        }
    
    async def shutdown(self):
        """Shutdown the assistant gracefully"""
        
        logger.info("Shutting down Sakana Assistant...")
        
        # Save current state
        if self.memory_manager:
            await self.memory_manager.close()
        
        if self.sandbox_executor:
            await self.sandbox_executor.cleanup()
        
        # Save metrics
        metrics_file = self.config.data_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        logger.info("Assistant shutdown complete")