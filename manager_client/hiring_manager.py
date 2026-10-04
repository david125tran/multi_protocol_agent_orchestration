# manager_client/hiring_manager.py

# Imports -------------------------------------------
import asyncio
import json
import sys

from datetime import datetime
from pathlib import Path


# Project Root -------------------------------------------
# Allows this file to be run directly from VS Code.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Project Imports -------------------------------------------
from providers.openai_client import (
    get_openai_client,
    LLM_MODEL,
)

from manager_client.protocols.client_a2a import (
    list_agents,
    get_agent_card,
    send_a2a_message,
    extract_a2a_text,
)

from manager_client.protocols.client_mcp import (
    get_all_applicant_resumes,
)

from manager_client.protocols.client_rest import (
    extend_offer,
)


# Constants / Variables -------------------------------------------
MAX_AGENT_STEPS = 40

APPLICANT_IDS = (
    "APP-1001",
    "APP-1002",
    "APP-1003",
    "APP-1004",
    "APP-1005",
)

OUTPUT_DIR = PROJECT_ROOT / "manager_client" / "output"
REPORT_PATH = OUTPUT_DIR / "hiring_report.md"


# Hiring Task -------------------------------------------
HIRING_TASK = """
Hire one applicant for the following position.

POSITION:
Senior Software Engineer

JOB DESCRIPTION:
We are looking for an experienced Senior Software Engineer with strong
experience in:

- Python
- API development
- cloud platforms
- observability
- distributed systems
- backend software engineering

Complete the hiring process and extend an offer to the applicant you determine
should be hired.
"""


# Manager Instructions -------------------------------------------
MANAGER_INSTRUCTIONS = """
You are the autonomous Hiring Manager for David Airlines.

Your goal is to hire ONE qualified applicant for the provided position.

You are a tool-using agent.

At each stage:

1. Review the evidence you already have.
2. Identify the most important missing information.
3. Choose the most appropriate available tool or discovered agent.
4. Observe the result.
5. Update your understanding.
6. Decide what to do next.

Do not follow a rigid predetermined workflow.

Adapt your actions based on the evidence you obtain.


## Available Capabilities


### A2A Agents

Some company capabilities are provided by discoverable A2A agents.

You are not told ahead of time which agents exist or exactly what they do.

Use the available discovery tools to:

- discover available agents
- inspect Agent Cards when needed
- delegate work to appropriate specialists

Use the exact agent_id returned by discovery.

Do not invent agents or capabilities that were not discovered.

When you need a company capability that is not directly available through
your built-in tools, examine the discovered agents and their Agent Cards to
determine whether an appropriate specialist exists.


### MCP

Applicant resume and professional-background information is available through
MCP.

The resume tool returns ALL available applicant resumes in a single call.

Call the resume tool once near the beginning of the hiring process and reuse
that information throughout the workflow.

Do not request resume information again unless there is a specific reason.


### REST

The final employment offer is made through the available REST action.

Only use the offer action after you have enough evidence to justify the hire
and have selected an approved salary.

Before selecting a final salary, obtain official compensation information
from an appropriate discovered company capability.

When asking HR for offer guidance, provide the complete approved compensation
information you obtained, including:

- position
- level
- minimum salary
- midpoint salary
- maximum salary

Do not shorten approved compensation information into only a salary range when
requesting final HR guidance if the full information is available.


## Progressive Agent Discovery

Do not inspect every discovered Agent Card preemptively.

Agent Cards should be inspected only when you have a current need that may be
served by that agent.

Use the lightweight agent directory to identify potentially relevant agents.

When a capability becomes necessary:
1. identify the likely relevant discovered agent
2. inspect that agent's Agent Card
3. use it if its advertised capabilities fit the need

Avoid retrieving Agent Cards for specialists whose capabilities are not yet
needed.

This keeps discovery incremental and avoids unnecessary work.


## Candidate Evaluation Strategy

Minimize unnecessary work, expensive operations, and token usage.

After retrieving all resumes, perform a lightweight comparison and select
NO MORE THAN TWO ACTIVE CANDIDATES for deeper investigation.

An active candidate is someone you are currently evaluating through interviews,
screening, HR review, or other deeper hiring activities.

Normally:

- Review all resumes once.
- Select the strongest one or two candidates for deeper evaluation.
- Interview promising candidates before requesting expensive background
  screening.
- Eliminate candidates when sufficient evidence shows they should not proceed.
- If an active candidate is eliminated, you may promote one additional
  candidate from the previously reviewed resume pool.
- Do not interview every applicant by default.
- Do not perform screening on every applicant.
- Prefer targeted follow-up questions when an important decision-changing gap
  may realistically be clarified.
- Treat scenario interview answers as simulated reasoning evidence.
- Scenario answers can help assess judgment, but they do not verify past work
  history or override the applicant data.
- Stop expanding the candidate pool when a sufficiently strong candidate has
  completed the necessary checks and can reasonably be hired.

The two-candidate guideline is intended to reduce unnecessary work.

It is not an absolute prohibition if unusual circumstances justify examining
another candidate.


## Practical Hiring Judgment

Do not expect any applicant to perfectly satisfy every requirement or provide
complete evidence for every desirable qualification.

Real candidates have strengths, weaknesses, unknowns, and areas that may require
on-the-job learning.

Evaluate candidates holistically.

A candidate may still be a strong hire when:

- they meet most of the important requirements
- their experience is strongly relevant to the core responsibilities
- their interview demonstrates sound judgment and an ability to reason through
  unfamiliar problems
- required screening passes
- there is no strong evidence that they are unqualified for the role

Distinguish carefully between:

- a demonstrated weakness
- a failed requirement
- missing or unavailable evidence

Missing or unavailable evidence is uncertainty.

It is NOT automatically negative evidence.

Do not treat the absence of a detailed historical example as proof that the
candidate lacks the underlying skill or experience.

The applicant records in this workflow are summarized professional profiles.
They may not contain complete project histories, production metrics, leadership
examples, incident details, or exact ownership boundaries.

Do not require information that is clearly unavailable from the applicant
records as an absolute condition for hiring.

If the candidate cannot provide a historical detail because it is not present
in the available record:

- acknowledge the uncertainty
- do not ask the same question repeatedly
- use the remaining evidence to make a reasonable hiring judgment

Scenario-based interview answers can provide useful evidence of technical
judgment when detailed historical evidence is unavailable.

A candidate may be hired when:

- their documented experience strongly aligns with the position
- their interview or scenario responses demonstrate appropriate judgment
- required screening passes
- no available evidence indicates a serious qualification problem

No candidate is expected to know everything.

Reasonable skill gaps, incomplete evidence, or areas for growth should not
automatically prevent a hire.

Prefer making a well-supported practical hiring decision over searching
indefinitely for a perfect candidate.


## Cost-Aware Evaluation

Treat hiring activities as having different costs.

Resume review is relatively cheap.

Interviews require additional time and model usage but are still cheaper than
pre-employment background screening.

Background screening is an expensive, late-stage operation.

Do not use background screening merely to rank candidates.

Normally, only request screening for a serious finalist who could realistically
receive the offer if the screening passes.

If the leading finalist fails required screening, reconsider the remaining
qualified candidates rather than screening everyone in advance.


## Interview Strategy

Use interviews to gather evidence that is not clear from the resume.

Focus interview questions on requirements that matter for the position.

When an important gap could realistically change the hiring decision, you may
use a targeted follow-up interview.

Do not keep requesting follow-up interviews merely because an applicant cannot
provide every desirable historical detail.

Do not ask an interview agent to invent past projects, accomplishments, or
experience that are not supported by the available applicant data.

When historical details cannot be established, scenario-based questions may be
used to evaluate technical judgment or decision-making without inventing
candidate history.

Treat hypothetical or scenario-based answers as evidence of reasoning ability,
not proof that the candidate performed that work previously.

If the available applicant record cannot support a more specific historical
answer, acknowledge the limitation and make a decision using the remaining
evidence.

Avoid repeatedly probing the same unavailable information.


## HR Guidance

HR is an advisory specialist.

HR does not make the final hiring decision.

HR can help evaluate:

- hiring readiness
- unresolved hiring concerns
- whether the available evidence supports proceeding with an offer
- appropriate salary positioning within approved compensation information

HR is not the source of truth for company salary ranges.

If approved compensation information is required, discover and use the
appropriate company capability rather than asking HR to invent or estimate it.

Consider consulting HR when:

- you are unsure whether a finalist is ready for an offer
- an important concern would benefit from independent review
- you want an independent review of the hiring decision
- you need guidance on where within an approved salary range an offer should
  fall

When requesting HR's final offer guidance, provide the relevant candidate
evidence, screening status, and complete approved compensation information.

Do not rely on HR to invent or estimate company salary ranges.

HR recommendations are advisory evidence, not mandatory approval.

If HR identifies a concern, determine whether that concern represents:

- a true disqualifying issue
- a meaningful risk that can reasonably be investigated
- or uncertainty caused by limited available evidence

You may disagree with HR when you have a reasonable evidence-based basis for
doing so.

You may proceed with a hire despite unresolved non-critical uncertainty when
the overall evidence reasonably supports the candidate's ability to succeed.

Do not allow HR to create an endless loop of repeated investigation into
information that is not available.


## Memory and Reuse

Remember and reuse information obtained earlier in the current hiring process.

Do not repeat a tool call just because time has passed.

Reuse known information such as:

- resumes
- interview results
- screening results
- discovered agent capabilities
- approved compensation information
- prior HR recommendations

Repeat or clarify a call only when new information is required or a previous
result was incomplete, ambiguous, failed, or the new request is materially
different.


## Hiring Rules

- Do not invent applicant information.
- Do not invent screening results.
- Do not invent compensation information.
- Do not invent A2A agents or capabilities.
- Do not assume an applicant passed required screening.
- Do not hire an applicant who clearly fails required pre-employment screening.
- A strong resume or interview does not override failed required screening.
- Obtain official compensation information before selecting a final salary.
- Use discovered specialized agents when their expertise is relevant.
- Extend an offer once the available evidence reasonably supports the
  candidate's ability to succeed in the role.
- Do not require perfect certainty or complete evidence for every desirable
  qualification.
- Missing information is not automatically a reason to reject a candidate.
- Do not reject an otherwise strong candidate solely because summarized
  applicant data lacks detailed historical examples.
- Once an applicant accepts an offer, the hiring task is complete.


## Audit Log Behavior

When useful, provide a SHORT decision summary explaining what you are doing
next and why.

These summaries should be concise and suitable for an audit log.

Do not provide hidden chain-of-thought or lengthy internal reasoning.

Good examples:

"APP-1001 and APP-1002 are the strongest candidates from the resume screen,
so I will interview them before requesting expensive screening."

"APP-1001 failed required screening and is eliminated. I will reconsider the
remaining qualified candidates."

"APP-1002 could not provide a detailed historical ownership example, but that
information is unavailable from the summarized applicant record. His resume,
scenario interview, and screening provide enough evidence to continue."

"HR identified an ownership-evidence concern. I will consider whether it is a
true qualification problem or simply unavailable historical detail."

"I need approved compensation information before selecting a salary, so I will
inspect the discovered company capabilities for an appropriate source."

Keep these explanations short.

Be autonomous, practical, and complete the hiring task.
"""


# Tool Definitions -------------------------------------------
TOOLS = [

    # --------------------------------------------------
    # A2A Discovery
    # --------------------------------------------------
    {
        "type": "function",
        "name": "list_agents",
        "description": (
            "Discover the A2A agents currently available in the "
            "David Airlines backend."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "get_agent_card",
        "description": (
            "Retrieve the Agent Card for a discovered A2A agent. "
            "Use the exact agent_id returned by list_agents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Exact agent_id returned by list_agents."
                    ),
                }
            },
            "required": [
                "agent_name"
            ],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "send_message_to_agent",
        "description": (
            "Send a task or question to a discovered A2A agent. "
            "Use the exact agent_id returned by list_agents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Exact agent_id returned by list_agents."
                    ),
                },
                "message": {
                    "type": "string",
                    "description": (
                        "Task, question, or relevant context to send "
                        "to the selected A2A agent."
                    ),
                },
            },
            "required": [
                "agent_name",
                "message",
            ],
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------
    # MCP
    # --------------------------------------------------
    {
        "type": "function",
        "name": "get_all_applicant_resumes",
        "description": (
            "Retrieve all resumes for the applicants in the current hiring "
            "task concurrently. Call this once before choosing the candidates "
            "to investigate further."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },

    # --------------------------------------------------
    # REST
    # --------------------------------------------------
    {
        "type": "function",
        "name": "extend_offer",
        "description": (
            "Extend a salary offer to the selected applicant. "
            "Use only after completing the necessary hiring review."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "applicant_id": {
                    "type": "string",
                    "description": (
                        "Applicant receiving the offer."
                    ),
                },
                "salary": {
                    "type": "number",
                    "description": (
                        "Annual salary being offered in US dollars."
                    ),
                },
            },
            "required": [
                "applicant_id",
                "salary",
            ],
            "additionalProperties": False,
        },
    },
]


# Markdown Audit Report -------------------------------------------
class HiringReport:
    """Record autonomous-manager decisions and tool activity as Markdown."""

    def __init__(
        self,
        output_path: Path,
    ):
        """Create a report that will be written to the supplied output path."""
        self.output_path = output_path
        self.lines = []

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def add(
        self,
        text: str,
    ):
        """Append raw Markdown text and echo it to the console."""
        self.lines.append(text)
        print(text)

    def section(
        self,
        emoji: str,
        title: str,
        body: str,
    ):
        """Append a titled report section with a matching console summary."""
        console_text = (
            f"\n{emoji} {title}\n"
            f"   {body}"
        )

        print(console_text)

        self.lines.append(
            f"\n## {emoji} {title}\n\n"
            f"{body}\n"
        )

    def decision(
        self,
        step: int,
        text: str,
    ):
        """Record the manager's short, user-visible decision for one step."""
        self.section(
            "🧠",
            f"Manager Decision: Step {step}",
            text,
        )

    def tool_call(
        self,
        step: int,
        tool_name: str,
        arguments: dict,
    ):
        """Record a requested tool name and its JSON-compatible arguments."""
        arguments_json = json.dumps(
            arguments,
            indent=2,
            default=str,
        )

        self.section(
            "🛠️",
            f"Tool Call: Step {step}",
            (
                f"**Tool:** `{tool_name}`\n\n"
                f"**Arguments:**\n\n"
                f"```json\n"
                f"{arguments_json}\n"
                f"```"
            ),
        )

    def tool_result(
        self,
        tool_name: str,
        result,
    ):
        """Record a tool result, formatting dictionaries as JSON Markdown."""
        if isinstance(result, str):
            formatted_result = result

        else:
            formatted_result = (
                "```json\n"
                + json.dumps(
                    result,
                    indent=2,
                    default=str,
                )
                + "\n```"
            )

        self.section(
            "📥",
            f"Tool Result: {tool_name}",
            formatted_result,
        )

    def save(self):
        """Write the completed Markdown audit report to the configured path."""
        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        header = (
            "# 👔 David Airlines Autonomous Hiring Workflow\n\n"
            f"**Generated:** {timestamp}\n\n"
            "---\n"
        )

        markdown = header + "\n".join(
            self.lines
        )

        self.output_path.write_text(
            markdown,
            encoding="utf-8",
        )


# A2A Error Handling -------------------------------------------
def is_a2a_error(result) -> bool:
    """Return whether an A2A helper result represents an error response."""
    if isinstance(result, str):
        return result.startswith("A2A Error:")

    if isinstance(result, dict):
        return "error" in result

    return False


# Tool Execution -------------------------------------------
async def execute_tool(
    tool_name: str,
    arguments: dict,
    report: HiringReport,
):
    """Run one manager tool call and add protocol-specific report context."""

    # --------------------------------------------------
    # A2A - Discover Agents
    # --------------------------------------------------
    if tool_name == "list_agents":

        report.section(
            "🔍",
            "A2A: Agent Discovery",
            "Discovering available A2A agents...",
        )

        result = await list_agents()

        return result

    # --------------------------------------------------
    # A2A - Agent Card
    # --------------------------------------------------
    if tool_name == "get_agent_card":

        agent_name = arguments["agent_name"]

        report.section(
            "🪪",
            "A2A: Agent Card",
            f"Inspecting capabilities for `{agent_name}`...",
        )

        result = await get_agent_card(
            agent_name
        )

        return result

    # --------------------------------------------------
    # A2A - Send Message
    # --------------------------------------------------
    if tool_name == "send_message_to_agent":

        agent_name = arguments["agent_name"]
        message = arguments["message"]

        report.section(
            "🤝",
            f"A2A: {agent_name}",
            (
                f"Sending task to `{agent_name}`.\n\n"
                f"**Message:**\n\n"
                f"{message}"
            ),
        )

        response = await send_a2a_message(
            agent_name,
            message,
        )

        result = extract_a2a_text(
            response
        )

        return result

    # --------------------------------------------------
    # MCP - Applicant Resumes
    # --------------------------------------------------
    if tool_name == "get_all_applicant_resumes":

        report.section(
            "📄",
            "MCP: Applicant Resume Screen",
            (
                "Retrieving all applicant resumes concurrently "
                "before narrowing the field..."
            ),
        )

        result = await get_all_applicant_resumes(
            APPLICANT_IDS
        )

        return result

    # --------------------------------------------------
    # REST - Extend Offer
    # --------------------------------------------------
    if tool_name == "extend_offer":

        applicant_id = arguments["applicant_id"]
        salary = arguments["salary"]

        report.section(
            "✉️",
            "REST: Extend Offer",
            (
                f"Extending a "
                f"`${salary:,.0f}` annual salary offer "
                f"to `{applicant_id}`..."
            ),
        )

        result = await extend_offer(
            applicant_id=applicant_id,
            salary=salary,
        )

        return result

    # --------------------------------------------------
    # Unknown Tool
    # --------------------------------------------------
    raise ValueError(
        f"Unknown tool requested: {tool_name}"
    )


# Serialize Tool Result -------------------------------------------
def serialize_tool_result(result) -> str:
    """Convert a tool result into the text returned to the manager model."""
    if isinstance(result, str):
        return result

    return json.dumps(
        result,
        indent=2,
        default=str,
    )


# Hiring Manager -------------------------------------------
async def run_hiring_manager(
    task: str,
    report: HiringReport,
):
    """
    Run the autonomous hiring loop until the manager completes the task.

    The model chooses tools, observes their results, updates its understanding,
    and continues until it reaches a final hiring decision or the safety limit.
    """
    client = get_openai_client()

    report.section(
        "👔",
        "Hiring Manager",
        "Starting autonomous hiring workflow.",
    )

    report.section(
        "🎯",
        "Hiring Task",
        task.strip(),
    )

    # --------------------------------------------------
    # Initial Request
    # --------------------------------------------------
    response = client.responses.create(
        model=LLM_MODEL,
        instructions=MANAGER_INSTRUCTIONS,
        input=task,
        tools=TOOLS,
    )

    step = 1

    # --------------------------------------------------
    # ReAct-style Loop
    # --------------------------------------------------
    while step <= MAX_AGENT_STEPS:

        # --------------------------------------------------
        # Capture user-visible manager commentary
        # --------------------------------------------------
        manager_text = response.output_text

        if manager_text:
            report.decision(
                step,
                manager_text,
            )

        # --------------------------------------------------
        # Find Tool Calls
        # --------------------------------------------------
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        # --------------------------------------------------
        # No Tools = Manager Finished
        # --------------------------------------------------
        if not tool_calls:

            final_text = (
                response.output_text
                or "Hiring workflow completed."
            )

            report.section(
                "🏁",
                "Hiring Manager Final Decision",
                final_text,
            )

            return final_text

        # --------------------------------------------------
        # Prepare Tool Calls
        # --------------------------------------------------
        tool_outputs = []

        remaining_steps = (
            MAX_AGENT_STEPS
            - step
            + 1
        )

        tool_calls = tool_calls[:remaining_steps]

        prepared_calls = []

        for tool_call in tool_calls:

            tool_name = tool_call.name

            try:
                arguments = json.loads(
                    tool_call.arguments
                )

            except json.JSONDecodeError:
                arguments = {
                    "raw_arguments": tool_call.arguments
                }

            report.tool_call(
                step=step + len(prepared_calls),
                tool_name=tool_name,
                arguments=arguments,
            )

            prepared_calls.append(
                (
                    tool_call,
                    tool_name,
                    arguments,
                )
            )

        # --------------------------------------------------
        # Execute Independent Tool Calls Concurrently
        # --------------------------------------------------
        results = await asyncio.gather(
            *(
                execute_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    report=report,
                )
                for _, tool_name, arguments in prepared_calls
            ),
            return_exceptions=True,
        )

        # --------------------------------------------------
        # Record Observations
        # --------------------------------------------------
        for (
            tool_call,
            tool_name,
            _,
        ), result in zip(
            prepared_calls,
            results,
        ):

            if isinstance(
                result,
                Exception,
            ):
                result = {
                    "error": type(result).__name__,
                    "message": str(result),
                }

            report.tool_result(
                tool_name=tool_name,
                result=result,
            )

            result_text = serialize_tool_result(
                result
            )

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": result_text,
                }
            )

        step += len(prepared_calls)

        # --------------------------------------------------
        # Safety Stop
        # --------------------------------------------------
        if step > MAX_AGENT_STEPS:

            message = (
                f"Agent stopped after "
                f"{MAX_AGENT_STEPS} tool steps to prevent "
                f"an uncontrolled loop."
            )

            report.section(
                "⚠️",
                "Maximum Steps Reached",
                message,
            )

            return message

        # --------------------------------------------------
        # Observation -> Next Reasoning Turn
        # --------------------------------------------------
        response = client.responses.create(
            model=LLM_MODEL,
            instructions=MANAGER_INSTRUCTIONS,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOLS,
        )

    return "Hiring manager exited unexpectedly."


# Main -------------------------------------------
async def main():
    """Run the demo hiring task and save its audit report."""

    report = HiringReport(
        output_path=REPORT_PATH
    )

    report.add(
        "\n"
        "The Hiring Manager has been given a hiring goal and "
        "will autonomously discover capabilities, gather "
        "evidence, delegate work, and attempt to make a hire."
        "\n"
    )

    try:

        final_result = await run_hiring_manager(
            task=HIRING_TASK,
            report=report,
        )

        report.section(
            "✅",
            "Workflow Complete",
            final_result,
        )

    except Exception as error:

        report.section(
            "❌",
            "Workflow Failed",
            (
                f"**Error:** `{type(error).__name__}`\n\n"
                f"{str(error)}"
            ),
        )

        raise

    finally:

        report.save()

        print()
        print("=" * 60)
        print("HIRING WORKFLOW FINISHED")
        print(f"Report saved to: {REPORT_PATH}")
        print("=" * 60)


# Entry Point -------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())