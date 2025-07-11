"""
File discovery through evolutionary self-learning
"""

import os
import random
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class FileCommand:
    """Represents a discovered file operation command"""
    command: str
    success_rate: float = 0.0
    attempts: int = 0
    discovered_at: str = datetime.now().isoformat()
    parameters: List[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []

class FileDiscoveryLearner:
    """Learns to find files through exploration and evolution"""
    
    def __init__(self):
        # Start with NO knowledge - will discover everything
        self.discovered_commands = {}
        self.successful_patterns = []
        self.failed_attempts = []
        self.exploration_history = []
        
        # Genetic material for evolving search strategies
        self.search_genome = {
            'command_pool': [],  # Will be discovered
            'path_strategies': [],  # Will be discovered
            'pattern_matchers': [],  # Will be discovered
            'exploration_depth': 1,
            'mutation_rate': 0.3
        }
        
    async def discover_file_commands(self) -> List[str]:
        """Discover available commands through exploration"""
        
        logger.info("Starting command discovery through exploration...")
        
        # Try random command-like strings
        potential_commands = self._generate_command_candidates()
        discovered = []
        
        for cmd in potential_commands:
            try:
                # Test if command exists
                result = subprocess.run(
                    ['which', cmd],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    logger.info(f"Discovered command: {cmd}")
                    discovered.append(cmd)
                    self.discovered_commands[cmd] = FileCommand(command=cmd)
                    
            except Exception as e:
                # Command doesn't exist or error
                pass
        
        # Update genome with discoveries
        self.search_genome['command_pool'] = discovered
        return discovered
    
    def _generate_command_candidates(self) -> List[str]:
        """Generate potential command names to test"""
        
        # Start with common patterns
        prefixes = ['', 'f', 'g', 'a']
        roots = ['find', 'search', 'locate', 'look', 'seek', 'scan', 'grep', 'ls']
        suffixes = ['', 'f', 'r', 'd']
        
        candidates = []
        
        # Generate combinations
        for prefix in prefixes:
            for root in roots:
                for suffix in suffixes:
                    candidates.append(prefix + root + suffix)
        
        # Add some completely random attempts
        for _ in range(10):
            random_cmd = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(2, 6)))
            candidates.append(random_cmd)
        
        return list(set(candidates))  # Remove duplicates
    
    async def evolve_search_strategy(self, target_file: str) -> Optional[str]:
        """Evolve a strategy to find a specific file"""
        
        logger.info(f"Evolving strategy to find: {target_file}")
        
        # Initialize population of search strategies
        population = self._create_initial_population()
        
        best_result = None
        generation = 0
        max_generations = 10
        
        while generation < max_generations and best_result is None:
            # Test each strategy
            results = []
            
            for strategy in population:
                result = await self._test_search_strategy(strategy, target_file)
                results.append((strategy, result))
                
                if result['found']:
                    best_result = result
                    self._record_success(strategy, result)
                    break
            
            if best_result:
                break
            
            # Evolve population
            population = self._evolve_population(results)
            generation += 1
            
            logger.info(f"Generation {generation}: No success yet, evolving...")
        
        return best_result
    
    def _create_initial_population(self) -> List[Dict[str, Any]]:
        """Create initial population of search strategies"""
        
        population = []
        
        # If we have discovered commands, use them
        if self.search_genome['command_pool']:
            for cmd in self.search_genome['command_pool']:
                # Create variations
                strategies = [
                    {
                        'command': cmd,
                        'args': ['-name', '{filename}'],
                        'paths': ['.']
                    },
                    {
                        'command': cmd,
                        'args': ['{filename}'],
                        'paths': ['/', '/home', '/mnt']
                    },
                    {
                        'command': cmd,
                        'args': ['-type', 'f', '-name', '{filename}'],
                        'paths': ['~']
                    }
                ]
                population.extend(strategies)
        
        # Add random exploration strategies
        for _ in range(5):
            population.append(self._generate_random_strategy())
        
        return population[:20]  # Limit population size
    
    def _generate_random_strategy(self) -> Dict[str, Any]:
        """Generate a random search strategy"""
        
        # Try to discover new patterns
        possible_args = [
            ['-name', '{filename}'],
            ['-iname', '{filename}'],
            ['--name', '{filename}'],
            ['{filename}'],
            ['-f', '{filename}'],
            ['/', '-name', '{filename}'],
            ['.', '-name', '{filename}']
        ]
        
        possible_paths = [
            ['.'], ['/'], ['~'], 
            ['/home'], ['/mnt'], ['/usr'],
            ['C:\\'], ['D:\\'], ['/mnt/c']
        ]
        
        return {
            'command': random.choice(self.search_genome.get('command_pool', ['find'])),
            'args': random.choice(possible_args),
            'paths': random.choice(possible_paths)
        }
    
    async def _test_search_strategy(self, strategy: Dict[str, Any], target_file: str) -> Dict[str, Any]:
        """Test a search strategy"""
        
        result = {
            'found': False,
            'path': None,
            'strategy': strategy,
            'error': None
        }
        
        try:
            # Build command
            cmd_parts = [strategy['command']]
            cmd_parts.extend(strategy.get('paths', []))
            
            # Replace filename placeholder
            args = [arg.replace('{filename}', target_file) for arg in strategy.get('args', [])]
            cmd_parts.extend(args)
            
            # Execute
            logger.debug(f"Testing command: {' '.join(cmd_parts)}")
            
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            
            if proc.returncode == 0 and stdout:
                # Found something
                paths = stdout.decode().strip().split('\n')
                if paths and paths[0]:
                    result['found'] = True
                    result['path'] = paths[0]
                    logger.info(f"Success! Found file at: {paths[0]}")
            
        except asyncio.TimeoutError:
            result['error'] = 'timeout'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _evolve_population(self, results: List[Tuple[Dict, Dict]]) -> List[Dict[str, Any]]:
        """Evolve population based on results"""
        
        # Sort by fitness (strategies that didn't error are better)
        def fitness(result):
            if result[1]['found']:
                return 100
            elif result[1]['error'] is None:
                return 10
            elif result[1]['error'] == 'timeout':
                return 5
            else:
                return 0
        
        results.sort(key=fitness, reverse=True)
        
        # Keep best strategies
        new_population = []
        elite_count = min(5, len(results) // 2)
        
        for i in range(elite_count):
            new_population.append(results[i][0])
        
        # Mutate and crossover
        while len(new_population) < 20:
            parent = random.choice(new_population[:elite_count] if new_population else results[:5])[0]
            child = self._mutate_strategy(parent)
            new_population.append(child)
        
        return new_population
    
    def _mutate_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate a search strategy"""
        
        mutated = strategy.copy()
        
        # Mutate command (rarely)
        if random.random() < 0.1 and self.search_genome['command_pool']:
            mutated['command'] = random.choice(self.search_genome['command_pool'])
        
        # Mutate arguments
        if random.random() < self.search_genome['mutation_rate']:
            arg_mutations = [
                ['-name', '{filename}'],
                ['-iname', '{filename}'],
                ['2>/dev/null', '-name', '{filename}'],
                ['-type', 'f', '-name', '{filename}'],
                ['-maxdepth', '5', '-name', '{filename}']
            ]
            mutated['args'] = random.choice(arg_mutations)
        
        # Mutate paths
        if random.random() < self.search_genome['mutation_rate']:
            path_mutations = [
                ['.'],
                ['..'],
                ['/'],
                ['~'],
                [os.path.expanduser('~')],
                ['/home'],
                [f'/home/{os.environ.get("USER", "user")}'],
                ['/mnt/c/Users'],
                [os.getcwd()]
            ]
            mutated['paths'] = random.choice(path_mutations)
        
        return mutated
    
    def _record_success(self, strategy: Dict[str, Any], result: Dict[str, Any]):
        """Record successful strategy for future use"""
        
        success_record = {
            'strategy': strategy,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        self.successful_patterns.append(success_record)
        
        # Update command success rate
        cmd = strategy['command']
        if cmd in self.discovered_commands:
            cmd_obj = self.discovered_commands[cmd]
            cmd_obj.attempts += 1
            cmd_obj.success_rate = (cmd_obj.success_rate * (cmd_obj.attempts - 1) + 1) / cmd_obj.attempts
        
        logger.info(f"Recorded successful pattern: {strategy}")
    
    async def learn_from_environment(self):
        """Explore the environment to learn about file structure"""
        
        logger.info("Exploring environment to learn file structure...")
        
        # Try to discover directory listing commands
        list_candidates = ['ls', 'dir', 'list', 'show']
        
        for cmd in list_candidates:
            try:
                result = subprocess.run([cmd], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    logger.info(f"Discovered listing command: {cmd}")
                    self.discovered_commands[f'{cmd}_list'] = FileCommand(command=cmd)
            except:
                pass
        
        # Learn about path structures
        self._discover_path_patterns()
    
    def _discover_path_patterns(self):
        """Discover common path patterns in the system"""
        
        # Try to understand path separators
        separators = ['/', '\\']
        
        # Test which paths exist
        test_paths = [
            '/', '/home', '/usr', '/etc',
            'C:\\', 'D:\\', 'C:\\Users',
            '~', '.', '..'
        ]
        
        discovered_paths = []
        
        for path in test_paths:
            if os.path.exists(os.path.expanduser(path)):
                discovered_paths.append(path)
                logger.info(f"Discovered valid path: {path}")
        
        self.search_genome['path_strategies'] = discovered_paths
    
    def get_learned_summary(self) -> Dict[str, Any]:
        """Get summary of what has been learned"""
        
        return {
            'discovered_commands': list(self.discovered_commands.keys()),
            'successful_patterns': len(self.successful_patterns),
            'known_paths': self.search_genome.get('path_strategies', []),
            'total_explorations': len(self.exploration_history),
            'best_commands': [
                {'command': cmd, 'success_rate': obj.success_rate}
                for cmd, obj in self.discovered_commands.items()
                if obj.success_rate > 0
            ]
        }