# app/protocols/a2a/router_a2a.py

# Imports -------------------------------------------
import os
import yaml

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Part,
    Task,
    TaskState,
    TaskStatus,
)
from app.protocols.a2a.agent_pipelines import (
    hr_pipeline,
    employee_background_pipeline,
    staff_accountant_pipeline,
    interview_pipeline,
)


# Agent Pipeline Registry -------------------------------------------
AGENT_PIPELINES = {
    "hr": hr_pipeline,
    "employee_background": employee_background_pipeline,
    "staff_accountant": staff_accountant_pipeline,
    "interview": interview_pipeline,
}


# A2A Agent Executor -------------------------------------------
class CompanyAgentExecutor(AgentExecutor):
    """Adapt a configured pipeline to the A2A server executor interface."""

    def __init__(self, agent_name: str):
        """Store the configured agent ID whose pipeline this executor runs."""
        self.agent_name = agent_name

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Run an A2A task and publish its final response as an artifact."""

        user_message = context.message
        task_id = context.task_id
        context_id = context.context_id

        if not user_message or not task_id or not context_id:
            return

        # A2A clients receive an explicit task before its response artifact.
        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_SUBMITTED
                ),
                history=[user_message],
            )
        )

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )

        query = context.get_user_input()

        print(f"AI AGENT: {self.agent_name}")
        print(f"USER SAID: {query}")

        response_text = await invoke_agent(
            agent_name=self.agent_name,
            query=query,
        )

        await updater.add_artifact(
            parts=[
                Part(text=response_text)
            ],
            name="response",
            last_chunk=True,
        )
        await updater.complete()

    

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Accept cancellation requests; this demo has no cancellable work."""
        pass


# Agent Dispatch -------------------------------------------
async def invoke_agent(agent_name: str, query: str) -> str:
    """Dispatch a user query to the pipeline registered for an agent ID."""
    pipeline = AGENT_PIPELINES.get(agent_name)
    return await pipeline(query)


# Agent Configuration -------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(
    SCRIPT_DIR,
    "agents_config.yaml",
)

with open(
    CONFIG_PATH,
    "r",
    encoding="utf-8",
) as file:
    config = yaml.safe_load(file)

agents = config["agents"]


# Route Collections -------------------------------------------
# These collections are imported by app/main.py and registered with FastAPI.
agent_cards = {}
jsonrpc_routes = []
agent_card_routes = []


# Build A2A Agents and Routes -------------------------------------------
# Convert each YAML agent definition into A2A SDK objects and routes.
for agent_name, agent_config in agents.items():
    skill_config = agent_config["skill"]
    card_config = agent_config["agent_card"]

    skill = AgentSkill(
        id=skill_config["id"],
        name=skill_config["name"],
        description=skill_config["description"],
        tags=skill_config["tags"],
        examples=skill_config["examples"],
        input_modes=skill_config["input_modes"],
        output_modes=skill_config["output_modes"],
    )

    interfaces = []
    for interface_config in card_config["supported_interfaces"]:
        interface = AgentInterface(
            protocol_binding=interface_config["protocol_binding"],
            protocol_version=interface_config["protocol_version"],
            url=interface_config["url"],
        )
        interfaces.append(interface)

    agent_card = AgentCard(
        name=card_config["name"],
        description=card_config["description"],
        version=card_config["version"],
        capabilities=AgentCapabilities(
            streaming=card_config["capabilities"]["streaming"]
        ),
        default_input_modes=card_config["default_input_modes"],
        default_output_modes=card_config["default_output_modes"],
        skills=[skill],
        supported_interfaces=interfaces,
    )

    agent_cards[agent_name] = agent_card

    request_handler = DefaultRequestHandler(
        agent_executor=CompanyAgentExecutor(agent_name),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    rpc_url = f"/a2a/{agent_name}/jsonrpc"

    routes = create_jsonrpc_routes(
        request_handler=request_handler,
        rpc_url=rpc_url,
    )

    jsonrpc_routes.extend(routes)

    card_routes = create_agent_card_routes(
        agent_card=agent_card,
        card_url=f"/a2a/{agent_name}/.well-known/agent-card.json",
    )

    agent_card_routes.extend(card_routes)

