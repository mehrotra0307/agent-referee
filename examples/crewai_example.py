"""
CrewAI agent wrapped with Agent Referee.

Run:
    pip install agent-referee crewai
    echo "OPENAI_API_KEY=your_key_here" > .env   # or GEMINI_API_KEY / ANTHROPIC_API_KEY
    python examples/crewai_example.py

Note: crewai pulls in a large dependency tree of its own (embeddings,
vector store clients, etc.) unrelated to Agent Referee. This example is
written against CrewAI's documented Agent/Task/Crew API but hasn't been
executed in this repo's own dev environment, to keep that environment
light — install it in your own project to run it for real.

Agent Referee never imports crewai anywhere. It only ever sees ask_agent()
at the bottom, an ordinary string-in, string-out function — everything
above that is 100% regular CrewAI code, unmodified.
"""

from crewai import Agent, Crew, Task

import referee

pizza_expert = Agent(
    role="Pizza Shop Assistant",
    goal="Answer customer questions about the menu, hours, and delivery accurately and briefly.",
    backstory=(
        "You work the counter at a busy pizza shop. You know the menu, the hours, and the "
        "delivery policy cold, and you keep answers short and friendly."
    ),
)

REFEREE_CONFIG = {
    "agent": {"name": "crewai-example"},
    "llm_provider": {"name": "openai"},
    "guardrails": {
        "input": {"pii_check": True, "injection_check": True, "rate_limit_per_session": 20},
        "output": {"pii_check": True, "toxicity_and_groundedness_check": False},
    },
    "observe": {"exporter": "console"},
}


@referee.protect(config=REFEREE_CONFIG)
def ask_agent(user_input: str) -> str:
    # This adapter is the entire integration surface: build a one-task
    # Crew per call, kick it off, and hand back the plain text result.
    task = Task(
        description=user_input,
        agent=pizza_expert,
        expected_output="A short, direct answer to the customer's question.",
    )
    crew = Crew(agents=[pizza_expert], tasks=[task])
    result = crew.kickoff()
    return result.raw


if __name__ == "__main__":
    print(ask_agent("What's a good topping combination for a margherita pizza?"))
