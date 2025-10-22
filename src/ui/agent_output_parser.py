"""
Agent Output Parser - Extracts structured events from agent output
"""
import re
import json
from typing import Dict, Any, Optional, Tuple


class AgentOutputParser:
    """Parses agent stdout/stderr to extract structured events"""

    # Patterns for different event types
    PATTERNS = {
        'tool_call': re.compile(r'\[(\w+)\]\s*Tool call:\s*(.+)', re.IGNORECASE),
        'result': re.compile(r'\[(\w+)\]\s*Result:\s*(.+)', re.IGNORECASE),
        'error': re.compile(r'\[(\w+)\]\s*Error:\s*(.+)', re.IGNORECASE),
        'success': re.compile(r'\[(\w+)\]\s*Success:\s*(.+)', re.IGNORECASE),
        'warning': re.compile(r'\[(\w+)\]\s*Warning:\s*(.+)', re.IGNORECASE),
        'info': re.compile(r'\[(\w+)\]\s*(?:INFO|Info):\s*(.+)', re.IGNORECASE),
        'debug': re.compile(r'\[(\w+)\]\s*(?:DEBUG|Debug):\s*(.+)', re.IGNORECASE),
        'json_data': re.compile(r'\[(\w+)\]\s*DATA:\s*(\{.+\})', re.IGNORECASE),
    }

    def parse_line(self, line: str, tool_name: str = 'unknown') -> Optional[Tuple[str, Any]]:
        """
        Parse a single line of agent output.

        Args:
            line: Output line from agent
            tool_name: Name of the tool (docker, github, etc.)

        Returns:
            Tuple of (event_type, payload) or None if not parseable
        """
        line = line.strip()
        if not line:
            return None

        # Try structured patterns first
        for event_type, pattern in self.PATTERNS.items():
            match = pattern.match(line)
            if match:
                matched_tool = match.group(1)
                content = match.group(2).strip()

                # Try to parse JSON if it looks like JSON
                if event_type == 'json_data' or (content.startswith('{') and content.endswith('}')):
                    try:
                        data = json.loads(content)
                        return (event_type, data)
                    except json.JSONDecodeError:
                        pass

                return (event_type, {'tool': matched_tool, 'message': content})

        # Check for JSON anywhere in the line
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\})*[^{}]*\}', line)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                return ('data', data)
            except json.JSONDecodeError:
                pass

        # Check for common patterns without tool prefix
        if 'error' in line.lower():
            return ('error', {'tool': tool_name, 'message': line})
        elif 'success' in line.lower() or 'completed' in line.lower():
            return ('success', {'tool': tool_name, 'message': line})
        elif 'warning' in line.lower():
            return ('warning', {'tool': tool_name, 'message': line})

        # Default: treat as log
        return ('log', {'tool': tool_name, 'message': line})

    def parse_docker_output(self, line: str) -> Optional[Tuple[str, Any]]:
        """
        Parse Docker-specific output patterns.

        Args:
            line: Output line from Docker agent

        Returns:
            Tuple of (event_type, payload) or None
        """
        # Try standard parsing first
        result = self.parse_line(line, 'docker')

        # Docker-specific patterns
        if 'container' in line.lower():
            # Extract container info if present
            container_pattern = re.compile(
                r'(?:Container|CONTAINER)\s+(?:ID\s+)?([a-f0-9]{12})\s+.*?(?:STATUS|Status)\s*:?\s*(\w+)',
                re.IGNORECASE
            )
            match = container_pattern.search(line)
            if match:
                return ('data', {
                    'type': 'container',
                    'id': match.group(1),
                    'status': match.group(2),
                    'raw': line
                })

        return result

    def parse_github_output(self, line: str) -> Optional[Tuple[str, Any]]:
        """
        Parse GitHub-specific output patterns.

        Args:
            line: Output line from GitHub agent

        Returns:
            Tuple of (event_type, payload) or None
        """
        # Parse Society of Mind agent messages
        # Pattern: [github] 🔧 GitHubOperator: ...
        # Pattern: [github] ✓ QAValidator: ...
        operator_match = re.match(r'\[github\]\s*🔧\s*GitHubOperator:\s*(.+)', line, re.IGNORECASE)
        if operator_match:
            return ('agent.message', {
                'tool': 'github',
                'agent': 'GitHubOperator',
                'role': 'operator',
                'message': operator_match.group(1).strip(),
                'icon': '🔧'
            })
        
        validator_match = re.match(r'\[github\]\s*✓\s*QAValidator:\s*(.+)', line, re.IGNORECASE)
        if validator_match:
            return ('agent.message', {
                'tool': 'github',
                'agent': 'QAValidator',
                'role': 'validator',
                'message': validator_match.group(1).strip(),
                'icon': '✓'
            })
        
        # Parse general [github] prefixed messages
        github_prefix_match = re.match(r'\[github\]\s*(.+)', line)
        if github_prefix_match:
            content = github_prefix_match.group(1).strip()
            # Check for tool calls
            if '🛠️' in content or 'Tool:' in content:
                return ('tool.call', {
                    'tool': 'github',
                    'message': content,
                    'icon': '🛠️'
                })
            # Check for completion markers
            if '====' in content or 'Task completed' in content:
                return ('status', {
                    'tool': 'github',
                    'message': content
                })
            # Default: agent log
            return ('log', {
                'tool': 'github',
                'message': content
            })
        
        result = self.parse_line(line, 'github')

        # GitHub-specific patterns (repos, issues, PRs)
        if 'repository' in line.lower() or 'repo' in line.lower():
            return ('data', {'type': 'repository', 'message': line})
        elif 'issue' in line.lower():
            return ('data', {'type': 'issue', 'message': line})
        elif 'pull request' in line.lower() or 'pr' in line.lower():
            return ('data', {'type': 'pull_request', 'message': line})

        return result

    def parse_supabase_output(self, line: str) -> Optional[Tuple[str, Any]]:
        """
        Parse Supabase-specific output patterns.

        Args:
            line: Output line from Supabase agent

        Returns:
            Tuple of (event_type, payload) or None
        """
        result = self.parse_line(line, 'supabase')

        # Supabase-specific patterns (SQL, tables, queries)
        if 'query' in line.lower() or 'select' in line.lower():
            return ('data', {'type': 'query', 'message': line})
        elif 'table' in line.lower():
            return ('data', {'type': 'table', 'message': line})

        return result

    def get_parser_for_tool(self, tool_name: str):
        """
        Get the appropriate parser function for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Parser function
        """
        parsers = {
            'docker': self.parse_docker_output,
            'github': self.parse_github_output,
            'supabase': self.parse_supabase_output,
        }

        return parsers.get(tool_name, lambda line: self.parse_line(line, tool_name))


# Global parser instance
_parser = AgentOutputParser()


def get_parser() -> AgentOutputParser:
    """Get the global parser instance"""
    return _parser
