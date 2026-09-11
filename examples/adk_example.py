"""
Google ADK (Agent Development Kit) agent wrapped with Agent Referee.

Run:
    pip install agent-referee google-adk python-dotenv
    echo "GEMINI_API_KEY=your_key_here" > .env
    python examples/adk_example.py

If you built your agent on ADK and deployed it on Google Cloud, this is the
adapter shape you need: ADK's own Runner speaks in Events, sessions, and
async calls, none of which Agent Referee needs to know about. The adapter
function at the bottom is the entire integration surface — it awaits your
existing ADK agent, pulls out the plain text of its final response, and
hands that string to Agent Referee. Agent Referee never imports adk
anywhere.

Verified against a real ADK LlmAgent + InMemoryRunner call in this project's
own dev environment (confirmed correct up to a real network request to
Gemini; only the dummy key in that test failed, not the ADK wiring itself).
"""

import asyncio
import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner

import referee

load_dotenv()

adk_agent = LlmAgent(
    name="pizza_shop_agent",
    model="gemini-3.1-flash-lite",
    instruction=(
        "You are the customer support agent for a pizza shop. Answer ONLY "
        "questions related to the shop: menu, hours, delivery, ordering."
    ),
)
runner = InMemoryRunner(agent=adk_agent)

REFEREE_CONFIG = {
    "agent": {"name": "adk-example"},
    "llm_provider": {"name": "gemini"},
    "guardrails": {
        "input": {"pii_check": True, "injection_check": True, "rate_limit_per_session": 20},
        "output": {"pii_check": True, "toxicity_and_groundedness_check": False},
    },
    "observe": {"exporter": "console"},
}


async def _ask_adk_agent(user_input: str) -> str:
    events = await runner.run_debug(user_input, quiet=True)
    for event in events:
        if event.is_final_response():
            return event.content.parts[0].text
    return "The agent didn't produce a final response."


@referee.protect(config=REFEREE_CONFIG)
def ask_agent(user_input: str) -> str:
    # This one line is the entire adapter: ADK's async, event-based world
    # in, a plain string out. Everything above this function is ordinary,
    # unmodified ADK code.
    return asyncio.run(_ask_adk_agent(user_input))


if __name__ == "__main__":
    print(ask_agent("What's a good topping combination for a margherita pizza?"))
