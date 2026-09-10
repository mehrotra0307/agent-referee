"""
Plain Python + OpenAI, no agent framework at all.

Run:
    pip install agent-referee openai python-dotenv
    echo "OPENAI_API_KEY=your_key_here" > .env
    python examples/plain_python_openai_example.py

Same wrapping pattern as the Gemini example — Agent Referee only ever sees
a function that takes a string and returns a string.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

import referee

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

REFEREE_CONFIG = {
    "agent": {"name": "plain-python-openai-example"},
    "llm_provider": {"name": "openai"},
    "guardrails": {
        "input": {"pii_check": True, "injection_check": True, "rate_limit_per_session": 20},
        "output": {"pii_check": True, "toxicity_and_groundedness_check": False},
    },
    "observe": {"exporter": "console"},
}


@referee.protect(config=REFEREE_CONFIG)
def ask_agent(user_input: str) -> str:
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": user_input}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(ask_agent("What's a good topping combination for a margherita pizza?"))
