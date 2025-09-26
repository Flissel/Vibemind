import json
import uuid
from typing import List, Tuple
import os 
from autogen_core import (
    FunctionCall,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import FunctionTool, Tool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from pydantic import BaseModel

class UserLogin(BaseModel):
    pass

class UserTask(BaseModel):
    context: List[LLMMessage]

class AgentResponse(BaseModel): 
    reply_to_topic_type: str
    context: List[LLMMessage]

class AIAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        system_message: SystemMessage,
        model_client: ChatCompletionClient,
        tools: List[Tool],
        delegate_tools: List[Tool],
        agent_topic_type: str,
        user_topic_type: str,
    ) -> None:
        super().__init__(description)
        self._system_message = system_message
        self._model_client = model_client
        self._tools = dict([(tool.name, tool) for tool in tools])
        self._tool_schema = [tool.schema for tool in tools]
        self._delegate_tools = dict([(tool.name, tool) for tool in delegate_tools])
        self._delegate_tool_schema = [tool.schema for tool in delegate_tools]
        self._agent_topic_type = agent_topic_type
        self._user_topic_type = user_topic_type

    @message_handler
    async def handle_task(self, message: UserTask, ctx: MessageContext) -> None:
        # Send the task to the LLM.
        llm_result = await self._model_client.create(
            messages=[self._system_message] + message.context,
            tools=self._tool_schema + self._delegate_tool_schema,
            cancellation_token=ctx.cancellation_token,
        )
        print(f"{'-'*80}\n{self.id.type}:\n{llm_result.content}", flush=True)
        # Process the LLM result.
        while isinstance(llm_result.content, list) and all(isinstance(m, FunctionCall) for m in llm_result.content):
            tool_call_results: List[FunctionExecutionResult] = []
            delegate_targets: List[Tuple[str, UserTask]] = []
            # Process each function call.
            for call in llm_result.content:
                arguments = json.loads(call.arguments)
                if call.name in self._tools:
                    # Execute the tool directly.
                    result = await self._tools[call.name].run_json(arguments, ctx.cancellation_token)
                    result_as_str = self._tools[call.name].return_value_as_string(result)
                    tool_call_results.append(FunctionExecutionResult(call_id=call.id, name=call.name, content=result_as_str))
                elif call.name in self._delegate_tools:
                    # Execute the tool to get the delegate agent's topic type.
                    result = await self._delegate_tools[call.name].run_json(arguments, ctx.cancellation_token)
                    topic_type = self._delegate_tools[call.name].return_value_as_string(result)
                    # Create the context for the delegate agent, including the function call and the result.
                    delegate_messages = list(message.context) + [
                        AssistantMessage(content=[call], source=self.id.type),
                        FunctionExecutionResultMessage(
                            content=[
                                FunctionExecutionResult(
                                    call_id=call.id, name=call.name, content=f"Transferred to {topic_type}. Adopt persona immediately."
                                )
                            ]
                        ),
                    ]
                    delegate_targets.append((topic_type, UserTask(context=delegate_messages)))
                else:
                    raise ValueError(f"Unknown tool: {call.name}")
            if len(delegate_targets) > 0:
                # Delegate the task to other agents by publishing messages to the corresponding topics.
                for topic_type, task in delegate_targets:
                    print(f"{'-'*80}\n{self.id.type}:\nTransferring to {topic_type}", flush=True)
                    await self.publish_message(task, topic_id=TopicId(topic_type, source=self.id.key))
            if len(tool_call_results) > 0:
                print(f"{'-'*80}\n{self.id.type}:\n{tool_call_results}", flush=True)
                # Make another LLM call with the results.
                message.context.extend(
                    [
                        AssistantMessage(content=llm_result.content, source=self.id.type),
                        FunctionExecutionResultMessage(content=tool_call_results),
                    ]
                )
                llm_result = await self._model_client.create(
                    messages=[self._system_message] + message.context,
                    tools=self._tool_schema + self._delegate_tool_schema,
                    cancellation_token=ctx.cancellation_token,
                )
                print(f"{'-'*80}\n{self.id.type}:\n{llm_result.content}", flush=True)
            else:
                # The task has been delegated, so we are done.
                return
        # The task has been completed, publish the final result.
        assert isinstance(llm_result.content, str)
        message.context.append(AssistantMessage(content=llm_result.content, source=self.id.type))
        await self.publish_message(
            AgentResponse(context=message.context, reply_to_topic_type=self._agent_topic_type),
            topic_id=TopicId(self._user_topic_type, source=self.id.key),
        )

class HumanAgent(RoutedAgent):
    def __init__(self, description: str, agent_topic_type: str, user_topic_type: str) -> None:
        super().__init__(description)
        self._agent_topic_type = agent_topic_type
        self._user_topic_type = user_topic_type

    @message_handler
    async def handle_user_task(self, message: UserTask, ctx: MessageContext) -> None:
        human_input = input("Senior Developer (Human) input: ")
        print(f"{'-'*80}\n{self.id.type}:\n{human_input}", flush=True)
        message.context.append(AssistantMessage(content=human_input, source=self.id.type))
        await self.publish_message(
            AgentResponse(context=message.context, reply_to_topic_type=self._agent_topic_type),
            topic_id=TopicId(self._user_topic_type, source=self.id.key),
        )

class UserAgent(RoutedAgent):
    def __init__(self, description: str, user_topic_type: str, agent_topic_type: str) -> None:
        super().__init__(description)
        self._user_topic_type = user_topic_type
        self._agent_topic_type = agent_topic_type

    @message_handler
    async def handle_user_login(self, message: UserLogin, ctx: MessageContext) -> None:
        print(f"{'-'*80}\nDevelopment Team Session Started - Session ID: {self.id.key}.")
        print("Welcome to the Development Team! Type your development request, bug report, or feature idea.")
        # Get the user's initial input after login.
        user_input = input("Developer: ")
        print(f"{'-'*80}\n{self.id.type}:\n{user_input}")
        await self.publish_message(
            UserTask(context=[UserMessage(content=user_input, source="Developer")]),
            topic_id=TopicId(self._agent_topic_type, source=self.id.key),
        )

    @message_handler
    async def handle_task_result(self, message: AgentResponse, ctx: MessageContext) -> None:
        # Get the user's input after receiving a response from an agent.
        user_input = input("Developer (type 'exit' to end session): ")
        print(f"{'-'*80}\n{self.id.type}:\n{user_input}", flush=True)
        if user_input.strip().lower() == "exit":
            print(f"{'-'*80}\nDevelopment session ended - Session ID: {self.id.key}.")
            return
        message.context.append(UserMessage(content=user_input, source="Developer"))
        await self.publish_message(
            UserTask(context=message.context), topic_id=TopicId(message.reply_to_topic_type, source=self.id.key)
        )

# Development Tools
def create_jira_ticket(title: str, description: str, priority: str = "Medium") -> str:
    ticket_id = f"DEV-{uuid.uuid4().hex[:8].upper()}"
    print(f"\n=== JIRA Ticket Created ===")
    print(f"Ticket ID: {ticket_id}")
    print(f"Title: {title}")
    print(f"Description: {description}")
    print(f"Priority: {priority}")
    print("=========================\n")
    return f"Ticket {ticket_id} created successfully"

def run_code_review(code_snippet: str, reviewer: str = "Senior Dev") -> str:
    print(f"\n=== Code Review ({reviewer}) ===")
    print(f"Code: {code_snippet}")
    print("Review: Code looks good! Minor suggestions:")
    print("- Add error handling")
    print("- Consider adding unit tests")
    print("- Documentation could be improved")
    print("Status: APPROVED")
    print("==========================\n")
    return "Code review completed - APPROVED with minor suggestions"

def deploy_to_environment(environment: str, branch: str = "main") -> str:
    print(f"\n=== Deployment to {environment.upper()} ===")
    print(f"Branch: {branch}")
    print(f"Environment: {environment}")
    print("Status: Deployment initiated...")
    print("✅ Build successful")
    print("✅ Tests passed")
    print("✅ Deployment complete")
    print("===============================\n")
    return f"Successfully deployed to {environment}"

def run_tests(test_type: str = "unit") -> str:
    print(f"\n=== Running {test_type.upper()} Tests ===")
    print("🧪 Test suite starting...")
    print("✅ Authentication tests: PASSED")
    print("✅ Database tests: PASSED")
    print("✅ API tests: PASSED")
    print("✅ Integration tests: PASSED")
    print("All tests passed! 🎉")
    print("========================\n")
    return f"{test_type.capitalize()} tests completed successfully"

def check_system_status() -> str:
    print(f"\n=== System Status Check ===")
    print("🔍 Checking system health...")
    print("✅ Database: Online")
    print("✅ API Gateway: Online")
    print("✅ Load Balancer: Online")
    print("✅ CDN: Online")
    print("System Status: ALL SERVICES HEALTHY")
    print("===========================\n")
    return "System status: All services operational"

async def main():
    # Create development tools
    create_ticket_tool = FunctionTool(create_jira_ticket, description="Create a JIRA ticket for bugs, features, or tasks")
    code_review_tool = FunctionTool(run_code_review, description="Submit code for review by senior developer")
    deploy_tool = FunctionTool(deploy_to_environment, description="Deploy code to staging or production environment")
    run_tests_tool = FunctionTool(run_tests, description="Run unit, integration, or end-to-end tests")
    system_status_tool = FunctionTool(check_system_status, description="Check current system and service status")

    # Agent topic types
    project_manager_topic_type = "ProjectManager"
    tech_lead_topic_type = "TechLead"
    backend_developer_topic_type = "BackendDeveloper"
    frontend_developer_topic_type = "FrontendDeveloper"
    qa_engineer_topic_type = "QAEngineer"
    devops_engineer_topic_type = "DevOpsEngineer"
    senior_developer_topic_type = "SeniorDeveloper"
    user_topic_type = "Developer"

    # Transfer functions
    def transfer_to_project_manager() -> str:
        return project_manager_topic_type

    def transfer_to_tech_lead() -> str:
        return tech_lead_topic_type

    def transfer_to_backend_developer() -> str:
        return backend_developer_topic_type

    def transfer_to_frontend_developer() -> str:
        return frontend_developer_topic_type

    def transfer_to_qa_engineer() -> str:
        return qa_engineer_topic_type

    def transfer_to_devops_engineer() -> str:
        return devops_engineer_topic_type

    def escalate_to_senior_developer() -> str:
        return senior_developer_topic_type

    # Transfer tools
    transfer_to_pm_tool = FunctionTool(transfer_to_project_manager, description="Transfer to Project Manager for feature planning, requirements, or roadmap discussions")
    transfer_to_tech_lead_tool = FunctionTool(transfer_to_tech_lead, description="Transfer to Tech Lead for architecture decisions, technical design, or code standards")
    transfer_to_backend_tool = FunctionTool(transfer_to_backend_developer, description="Transfer to Backend Developer for API development, database design, or server-side logic")
    transfer_to_frontend_tool = FunctionTool(transfer_to_frontend_developer, description="Transfer to Frontend Developer for UI/UX implementation, client-side logic, or responsive design")
    transfer_to_qa_tool = FunctionTool(transfer_to_qa_engineer, description="Transfer to QA Engineer for testing, bug reports, or quality assurance")
    transfer_to_devops_tool = FunctionTool(transfer_to_devops_engineer, description="Transfer to DevOps Engineer for deployment, infrastructure, or CI/CD issues")
    escalate_to_senior_tool = FunctionTool(escalate_to_senior_developer, description="Escalate to Senior Developer for complex technical issues or architectural decisions")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=OPENAI_API_KEY,
    )

    runtime = SingleThreadedAgentRuntime()

    # Register Project Manager Agent
    project_manager_agent_type = await AIAgent.register(
        runtime,
        type=project_manager_topic_type,
        factory=lambda: AIAgent(
            description="A project manager agent.",
            system_message=SystemMessage(
                content="You are a Project Manager for a software development team. "
                "Always be brief and professional. "
                "Handle feature requests, requirements gathering, sprint planning, and roadmap discussions. "
                "Create JIRA tickets for new features and coordinate with the development team. "
                "If the request is technical implementation, transfer to the appropriate developer. "
                "If it's testing related, transfer to QA. If it's deployment related, transfer to DevOps."
            ),
            model_client=model_client,
            tools=[create_ticket_tool],
            delegate_tools=[
                transfer_to_tech_lead_tool,
                transfer_to_backend_tool,
                transfer_to_frontend_tool,
                transfer_to_qa_tool,
                transfer_to_devops_tool,
                escalate_to_senior_tool,
            ],
            agent_topic_type=project_manager_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=project_manager_topic_type, agent_type=project_manager_agent_type.type))

    # Register Tech Lead Agent
    tech_lead_agent_type = await AIAgent.register(
        runtime,
        type=tech_lead_topic_type,
        factory=lambda: AIAgent(
            description="A technical lead agent.",
            system_message=SystemMessage(
                content="You are a Technical Lead for a software development team. "
                "Always be brief and technical. "
                "Handle architecture decisions, technical design, code standards, and technical reviews. "
                "Conduct code reviews and provide technical guidance. "
                "If implementation is needed, transfer to the appropriate developer. "
                "If testing is needed, transfer to QA. If deployment is needed, transfer to DevOps."
            ),
            model_client=model_client,
            tools=[code_review_tool],
            delegate_tools=[
                transfer_to_pm_tool,
                transfer_to_backend_tool,
                transfer_to_frontend_tool,
                transfer_to_qa_tool,
                transfer_to_devops_tool,
                escalate_to_senior_tool,
            ],
            agent_topic_type=tech_lead_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=tech_lead_topic_type, agent_type=tech_lead_agent_type.type))

    # Register Backend Developer Agent
    backend_developer_agent_type = await AIAgent.register(
        runtime,
        type=backend_developer_topic_type,
        factory=lambda: AIAgent(
            description="A backend developer agent.",
            system_message=SystemMessage(
                content="You are a Backend Developer specializing in APIs, databases, and server-side logic. "
                "Always be brief and technical. "
                "Handle API development, database design, server-side implementation, and backend architecture. "
                "If you need project planning, transfer to PM. If you need architecture review, transfer to Tech Lead. "
                "If you need UI work, transfer to Frontend. If you need testing, transfer to QA. "
                "If you need deployment, transfer to DevOps."
            ),
            model_client=model_client,
            tools=[run_tests_tool],
            delegate_tools=[
                transfer_to_pm_tool,
                transfer_to_tech_lead_tool,
                transfer_to_frontend_tool,
                transfer_to_qa_tool,
                transfer_to_devops_tool,
                escalate_to_senior_tool,
            ],
            agent_topic_type=backend_developer_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=backend_developer_topic_type, agent_type=backend_developer_agent_type.type))

    # Register Frontend Developer Agent
    frontend_developer_agent_type = await AIAgent.register(
        runtime,
        type=frontend_developer_topic_type,
        factory=lambda: AIAgent(
            description="A frontend developer agent.",
            system_message=SystemMessage(
                content="You are a Frontend Developer specializing in UI/UX, client-side logic, and responsive design. "
                "Always be brief and user-focused. "
                "Handle UI implementation, client-side development, responsive design, and user experience. "
                "If you need project planning, transfer to PM. If you need architecture review, transfer to Tech Lead. "
                "If you need backend API work, transfer to Backend. If you need testing, transfer to QA. "
                "If you need deployment, transfer to DevOps."
            ),
            model_client=model_client,
            tools=[run_tests_tool],
            delegate_tools=[
                transfer_to_pm_tool,
                transfer_to_tech_lead_tool,
                transfer_to_backend_tool,
                transfer_to_qa_tool,
                transfer_to_devops_tool,
                escalate_to_senior_tool,
            ],
            agent_topic_type=frontend_developer_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=frontend_developer_topic_type, agent_type=frontend_developer_agent_type.type))

    # Register QA Engineer Agent
    qa_engineer_agent_type = await AIAgent.register(
        runtime,
        type=qa_engineer_topic_type,
        factory=lambda: AIAgent(
            description="A QA engineer agent.",
            system_message=SystemMessage(
                content="You are a QA Engineer specializing in testing, quality assurance, and bug reports. "
                "Always be brief and quality-focused. "
                "Handle testing strategies, bug reporting, test automation, and quality assurance processes. "
                "Run different types of tests and ensure code quality. "
                "If you need project planning, transfer to PM. If you need technical architecture, transfer to Tech Lead. "
                "If you need implementation fixes, transfer to the appropriate developer. "
                "If you need deployment, transfer to DevOps."
            ),
            model_client=model_client,
            tools=[run_tests_tool, create_ticket_tool],
            delegate_tools=[
                transfer_to_pm_tool,
                transfer_to_tech_lead_tool,
                transfer_to_backend_tool,
                transfer_to_frontend_tool,
                transfer_to_devops_tool,
                escalate_to_senior_tool,
            ],
            agent_topic_type=qa_engineer_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=qa_engineer_topic_type, agent_type=qa_engineer_agent_type.type))

    # Register DevOps Engineer Agent
    devops_engineer_agent_type = await AIAgent.register(
        runtime,
        type=devops_engineer_topic_type,
        factory=lambda: AIAgent(
            description="A DevOps engineer agent.",
            system_message=SystemMessage(
                content="You are a DevOps Engineer specializing in deployment, infrastructure, and CI/CD processes. "
                "Always be brief and infrastructure-focused. "
                "Handle deployments, infrastructure management, CI/CD pipelines, and system monitoring. "
                "Deploy code to different environments and monitor system health. "
                "If you need project planning, transfer to PM. If you need technical architecture, transfer to Tech Lead. "
                "If you need implementation changes, transfer to the appropriate developer. "
                "If you need testing, transfer to QA."
            ),
            model_client=model_client,
            tools=[deploy_tool, system_status_tool],
            delegate_tools=[
                transfer_to_pm_tool,
                transfer_to_tech_lead_tool,
                transfer_to_backend_tool,
                transfer_to_frontend_tool,
                transfer_to_qa_tool,
                escalate_to_senior_tool,
            ],
            agent_topic_type=devops_engineer_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=devops_engineer_topic_type, agent_type=devops_engineer_agent_type.type))

    # Register Senior Developer (Human) Agent
    senior_developer_agent_type = await HumanAgent.register(
        runtime,
        type=senior_developer_topic_type,
        factory=lambda: HumanAgent(
            description="A senior developer (human) agent.",
            agent_topic_type=senior_developer_topic_type,
            user_topic_type=user_topic_type,
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=senior_developer_topic_type, agent_type=senior_developer_agent_type.type))

    # Register User Agent
    user_agent_type = await UserAgent.register(
        runtime,
        type=user_topic_type,
        factory=lambda: UserAgent(
            description="A developer user agent.",
            user_topic_type=user_topic_type,
            agent_topic_type=project_manager_topic_type,  # Start with Project Manager
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=user_topic_type, agent_type=user_agent_type.type))

    # Start the runtime
    runtime.start()

    # Create a new session for the user
    session_id = str(uuid.uuid4())
    await runtime.publish_message(UserLogin(), topic_id=TopicId(user_topic_type, source=session_id))

    # Run until completion
    await runtime.stop_when_idle()

import asyncio
if __name__ == "__main__":
    asyncio.run(main())