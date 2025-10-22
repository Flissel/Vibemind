import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Load .env for environment variables
try:
    import dotenv
    # Find .env in project root (4 levels up from agent.py)
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env')
    dotenv.load_dotenv(dotenv_path=env_path)
except Exception:
    pass

# Autogen / MCP imports - Society of Mind pattern
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench
from autogen_ext.tools.mcp import StdioServerParams, create_mcp_server_session, mcp_server_tools
from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core.model_context import BufferedChatCompletionContext
from pydantic import BaseModel

# Fetch plugin imports FIRST (before sys.path.insert!)
from fetch_constants import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TASK_PROMPT,
    DEFAULT_FETCH_OPERATOR_PROMPT,
    DEFAULT_QA_VALIDATOR_PROMPT,
    DEFAULT_USER_CLARIFICATION_PROMPT,
)
from event_task import start_fetch_ui_server
from user_interaction_utils import create_ask_user_tool

# Shared module imports AFTER local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from event_server import EventServer
from constants import (
    MCP_EVENT_SESSION_ANNOUNCE,
    MCP_EVENT_AGENT_MESSAGE,
    MCP_EVENT_AGENT_ERROR,
    MCP_EVENT_TASK_COMPLETE,
    MCP_EVENT_CONVERSATION_HISTORY,
    SESSION_STATE_CREATED,
    SESSION_STATE_RUNNING,
    SESSION_STATE_STOPPED,
    SESSION_STATE_ERROR,
)
from model_utils import get_model_client
from logging_utils import setup_logging


class FetchAgentConfig(BaseModel):
    """Configuration for Fetch MCP agent"""
    session_id: str
    name: str
    model: str
    task: str


class FetchMCPAgent:
    """Fetch MCP Agent with Society of Mind architecture"""

    def __init__(self, config: FetchAgentConfig):
        self.config = config
        self.session_id = config.session_id
        self.logger = setup_logging(f"fetch_agent_{self.session_id}")
        self.event_server = None
        self.event_port = None
        self.mcp_session = None
        self.model_client = None
        self.team = None
        self.conversation_history = []

    async def initialize(self):
        """Initialize the agent with event server and MCP session"""
        try:
            # Start event server
            self.event_server = EventServer(session_id=self.session_id, tool_name="fetch")
            self.event_port = await self.event_server.start()
            self.logger.info(f"Event server started on port {self.event_port}")

            # Send SESSION_ANNOUNCE
            await self.event_server.send_event({
                "type": MCP_EVENT_SESSION_ANNOUNCE,
                "session_id": self.session_id,
                "host": "127.0.0.1",
                "port": self.event_port,
                "status": SESSION_STATE_CREATED,
                "timestamp": time.time()
            })

            # Initialize model client
            self.model_client = get_model_client(self.config.model)
            self.logger.info(f"Model client initialized: {self.config.model}")

            # Set up Fetch MCP server parameters
            server_params = StdioServerParams(
                command="cmd.exe" if sys.platform == 'win32' else "sh",
                args=["/c", "npx", "-y", "@modelcontextprotocol/server-fetch"] if sys.platform == 'win32' else ["-c", "npx -y @modelcontextprotocol/server-fetch"],
                env={}
            )

            # Create MCP session (context manager)
            self.mcp_session = create_mcp_server_session(server_params)
            self.session_context = await self.mcp_session.__aenter__()
            self.logger.info("Fetch MCP session created")

            # Create Society of Mind team
            await self._create_team()

            self.logger.info("Fetch agent initialized successfully")

        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}", exc_info=True)
            await self.event_server.send_event({
                "type": MCP_EVENT_AGENT_ERROR,
                "error": str(e),
                "status": SESSION_STATE_ERROR,
                "timestamp": time.time()
            })
            raise

    async def _create_team(self):
        """Create Society of Mind team with fetch-specific agents"""
        # Get Fetch MCP tools
        fetch_tools = await mcp_server_tools(self.session_context)

        # Create ask_user tool for clarifications
        ask_user_tool = create_ask_user_tool(self.event_server, self.session_id)

        # Fetch Operator Agent - Main HTTP request expert
        fetch_operator = AssistantAgent(
            name="Fetch_Operator",
            model_client=self.model_client,
            tools=fetch_tools + [ask_user_tool],
            system_message=DEFAULT_FETCH_OPERATOR_PROMPT,
            model_context=BufferedChatCompletionContext(buffer_size=10)
        )

        # QA Validator Agent - Validates results
        qa_validator = AssistantAgent(
            name="QA_Validator",
            model_client=self.model_client,
            tools=[],
            system_message=DEFAULT_QA_VALIDATOR_PROMPT,
            model_context=BufferedChatCompletionContext(buffer_size=5)
        )

        # Create Round Robin team
        self.team = RoundRobinGroupChat(
            participants=[fetch_operator, qa_validator],
            termination_condition=TextMentionTermination("TASK_COMPLETE")
        )

        self.logger.info("Society of Mind team created with Fetch_Operator and QA_Validator")

    async def run_task(self):
        """Run the fetch task"""
        try:
            await self.event_server.send_event({
                "type": MCP_EVENT_AGENT_MESSAGE,
                "message": f"Starting fetch task: {self.config.task}",
                "status": SESSION_STATE_RUNNING,
                "timestamp": time.time()
            })

            # Run the team
            result = await self.team.run(task=self.config.task)

            # Extract conversation history
            for msg in result.messages:
                self.conversation_history.append({
                    "source": msg.source,
                    "content": str(msg.content),
                    "timestamp": time.time()
                })

            # Send completion event
            await self.event_server.send_event({
                "type": MCP_EVENT_TASK_COMPLETE,
                "result": str(result.messages[-1].content) if result.messages else "Task completed",
                "status": SESSION_STATE_STOPPED,
                "timestamp": time.time()
            })

            # Send conversation history
            await self.event_server.send_event({
                "type": MCP_EVENT_CONVERSATION_HISTORY,
                "history": self.conversation_history,
                "timestamp": time.time()
            })

            self.logger.info("Task completed successfully")

        except Exception as e:
            self.logger.error(f"Task execution error: {str(e)}", exc_info=True)
            await self.event_server.send_event({
                "type": MCP_EVENT_AGENT_ERROR,
                "error": str(e),
                "status": SESSION_STATE_ERROR,
                "timestamp": time.time()
            })

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.mcp_session:
                await self.mcp_session.__aexit__(None, None, None)
            if self.event_server:
                await self.event_server.stop()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}", exc_info=True)


async def main():
    """Main entry point"""
    import argparse

    # Parse command-line arguments (compatible with session manager)
    parser = argparse.ArgumentParser(description='Fetch MCP Agent')
    parser.add_argument('--session-id', required=False, help='Session ID')
    parser.add_argument('--name', default='fetch-session', help='Session name')
    parser.add_argument('--model', default='openai/gpt-4o-mini', help='Model to use')
    parser.add_argument('--task', default='Fetch web content', help='Task to execute')
    parser.add_argument('config_json', nargs='?', help='JSON config (alternative to flags)')

    args = parser.parse_args()

    try:
        # Support both JSON arg and command-line flags
        if args.config_json:
            config_dict = json.loads(args.config_json)
        elif args.session_id:
            config_dict = {
                'session_id': args.session_id,
                'name': args.name,
                'model': args.model,
                'task': args.task
            }
        else:
            print(json.dumps({"error": "Missing session config (provide --session-id or JSON)"}), file=sys.stderr)
            sys.exit(1)

        config = FetchAgentConfig(**config_dict)

        agent = FetchMCPAgent(config)
        await agent.initialize()

        # Start UI server in background
        asyncio.create_task(start_fetch_ui_server(config.session_id, agent.event_port))

        # Run the task
        await agent.run_task()

        # Cleanup
        await agent.cleanup()

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
