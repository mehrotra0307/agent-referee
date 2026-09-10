"""
LangGraph agent wrapped with Agent Referee.

Run:
    pip install agent-referee langgraph google-genai python-dotenv
    echo "GEMINI_API_KEY=your_key_here" > .env
    python examples/langgraph_example.py

Agent Referee never imports LangGraph and has no idea a graph is involved
anywhere — it only ever sees ask_agent() at the bottom, an ordinary
string-in, string-out function. Everything above that is 100% regular
LangGraph code, unmodified.
"""

import os
from typing import TypedDict

from dotenv import load_dotenv
from google import genai
from langgraph.graph import END, StateGraph

import referee

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class AgentState(TypedDict):
    user_input: str
    response: str


def call_llm_node(state: AgentState) -> dict:
    result = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=state["user_input"],
    )
    return {"response": result.text}


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("call_llm", call_llm_node)
    workflow.set_entry_point("call_llm")
    workflow.add_edge("call_llm", END)
    return workflow.compile()


graph = build_graph()

REFEREE_CONFIG = {
    "agent": {"name": "langgraph-example"},
    "llm_provider": {"name": "gemini"},
    "guardrails": {
        "input": {"pii_check": True, "injection_check": True, "rate_limit_per_session": 20},
        "output": {"pii_check": True, "toxicity_and_groundedness_check": False},
    },
    "observe": {"exporter": "console"},
}


@referee.protect(config=REFEREE_CONFIG)
def ask_agent(user_input: str) -> str:
    # This adapter is the entire integration surface: LangGraph's state
    # dict in and out, Agent Referee's plain string in and out.
    result = graph.invoke({"user_input": user_input, "response": ""})
    return result["response"]


if __name__ == "__main__":
    print(ask_agent("What's a good topping combination for a margherita pizza?"))
