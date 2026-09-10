"""
Plain Python + Gemini, no agent framework at all.

Run:
    pip install agent-referee google-genai python-dotenv
    echo "GEMINI_API_KEY=your_key_here" > .env
    python examples/plain_python_gemini_example.py

This is the simplest possible shape Agent Referee wraps: any function that
takes a string and returns a string. Everything below `@referee.protect`
is a completely ordinary Gemini call — Agent Referee doesn't know or care
that it's Gemini specifically.
"""

import os

from dotenv import load_dotenv
from google import genai

import referee

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

REFEREE_CONFIG = {
    "agent": {"name": "plain-python-gemini-example"},
    "llm_provider": {"name": "gemini"},
    "guardrails": {
        "input": {"pii_check": True, "injection_check": True, "rate_limit_per_session": 20},
        "output": {"pii_check": True, "toxicity_and_groundedness_check": False},
    },
    "observe": {"exporter": "console"},
}


@referee.protect(config=REFEREE_CONFIG)
def ask_agent(user_input: str) -> str:
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=user_input,
    )
    return response.text


if __name__ == "__main__":
    print(ask_agent("What's a good topping combination for a margherita pizza?"))
