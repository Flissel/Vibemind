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

# Sequential Thinking plugin imports FIRST (before sys.path.insert!)
from thinking_constants import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TASK_PROMPT,
    DEFAULT_THINKER_PROMPT,
    DEFAULT_QA_VALIDATOR_PROMPT,
)
from event_task import start_thinking_ui_server
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


class ThinkingAgentConfig(BaseModel):
    """Configuration for Sequential Thinking MCP agent"""
    session_id: str
    name: str
    model: str
    task: str
    disable_thought_logging: bool = False


class SequentialThinkingMCPAgent:
    """Sequential Thinking MCP Agent with Society of Mind architecture"""

    def __init__(self, config: ThinkingAgentConfig):
        self.config = config
        self.session_id = config.session_id
        self.logger = setup_logging(f"thinking_agent_{self.session_id}")
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
            self.event_server = EventServer(session_id=self.session_id, tool_name="sequential-thinking")
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

            # Set up Sequential Thinking MCP server parameters
            thinking_env = {
                "DISABLE_THOUGHT_LOGGING": "true" if self.config.disable_thought_logging else "false"
            }

            server_params = StdioServerParams(
                command="cmd.exe" if sys.platform == 'win32' else "sh",
                args=["/c", "npx", "-y", "@modelcontextprotocol/server-sequential-thinking"] if sys.platform == 'win32' else ["-c", "npx -y @modelcontextprotocol/server-sequential-thinking"],
                env=thinking_env
            )

            # Create MCP session
            self.mcp_session = await create_mcp_server_session(server_params, read_timeout_seconds=120)
            self.logger.info("Sequential Thinking MCP session created")

            # Create Society of Mind team
            await self._create_team()

            self.logger.info("Sequential Thinking agent initialized successfully")

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
        """Create Society of Mind team with thinking-specific agents"""
        # Get Sequential Thinking MCP tools
        thinking_tools = await mcp_server_tools(self.mcp_session, read_timeout_seconds=120)

        # Create ask_user tool for clarifications
        ask_user_tool = create_ask_user_tool(self.event_server, self.session_id)

        # Thinker Agent - Uses sequential thinking for complex problems
        thinker = AssistantAgent(
            name="Thinker",
            model_client=self.model_client,
            tools=thinking_tools + [ask_user_tool],
            system_message=DEFAULT_THINKER_PROMPT,
            model_context=BufferedChatCompletionContext(buffer_size=15)
        )

        # QA Validator Agent - Validates thinking process and results
        qa_validator = AssistantAgent(
            name="QA_Validator",
            model_client=self.model_client,
            tools=[],
            system_message=DEFAULT_QA_VALIDATOR_PROMPT,
            model_context=BufferedChatCompletionContext(buffer_size=5)
        )

        # Create Round Robin team
        self.team = RoundRobinGroupChat(
            participants=[thinker, qa_validator],
            termination_condition=TextMentionTermination("TASK_COMPLETE")
        )

        self.logger.info("Society of Mind team created with Thinker and QA_Validator")

    async def run_task(self):
        """Run the sequential thinking task"""
        try:
            await self.event_server.send_event({
                "type": MCP_EVENT_AGENT_MESSAGE,
                "message": f"Starting sequential thinking task: {self.config.task}",
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
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing session config JSON"}))
        sys.exit(1)

    try:
        config_json = sys.argv[1]
        config_dict = json.loads(config_json)
        config = ThinkingAgentConfig(**config_dict)

        agent = SequentialThinkingMCPAgent(config)
        await agent.initialize()

        # Start UI server in background
        asyncio.create_task(start_thinking_ui_server(agent.session_id, agent.event_port))

        # Run task
        await agent.run_task()

        # Keep alive for event streaming
        await asyncio.sleep(3600)  # 1 hour max

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    finally:
        if 'agent' in locals():
            await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
