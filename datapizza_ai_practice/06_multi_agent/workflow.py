"""Multi-agent workflow: tech lead orchestrates data engineer + data scientist agents.

The tech lead delegates tasks to sub-agents via can_call(), each with a code interpreter.
Usage: python 06_multi_agent/workflow.py  (type 'quit' to exit)
Requires: OPENAI_API_KEY or GOOGLE_API_KEY in .env
"""
import os

from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.clients.google import GoogleClient
from datapizza.tools import tool
from dotenv import load_dotenv
from prompts.tech_lead import SYSTEM_PROMPT as TECH_LEAD_SYSTEM_PROMPT
from prompts.data_engineer import SYSTEM_PROMPT as DATA_ENGINEER_SYSTEM_PROMPT
from prompts.data_scientist import SYSTEM_PROMPT as DATA_SCIENTIST_SYSTEM_PROMPT
from tools.execute_code import execute_code

load_dotenv()

SYSTEM_PROMPT = "You are a helpful assistant that can answer questions and help with tasks."

PROVIDER = "openai"

if PROVIDER == "openai":
    client = OpenAIClient(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-5.1",
        system_prompt=SYSTEM_PROMPT,
    )
elif PROVIDER == "google":
    client = GoogleClient(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-flash-latest",
        system_prompt=SYSTEM_PROMPT,
    )
else:
    raise ValueError("Invalid PROVIDER. Use 'openai' or 'google'.")

code_interpreter_state = {}

@tool
def code_interpreter(code: str, agent_name: str) -> str:
    """Use this tool to execute Python code.
    - If it tells you the code is not safe, return this information as a response
    - If it gives you an error due to code execution, correct the code according to the error message and try again
    - If it returns results, return them as a response
    - Always end with a print statement to verify the output"""
    print(f"Executing code from {agent_name}...")
    print(f"Code:\n{code}")
    state = code_interpreter_state.get(f"{agent_name}_state", {})
    return execute_code(code, state)

tech_lead_agent = Agent(
    name="tech_lead",
    client=client,
    system_prompt=TECH_LEAD_SYSTEM_PROMPT,
    stateless=False # Memory persistence for the agent
)

data_engineer_agent = Agent(
    name="data_engineer",
    client=client,
    system_prompt=DATA_ENGINEER_SYSTEM_PROMPT,
    tools=[code_interpreter],
)

data_scientist_agent = Agent(
    name="data_scientist",
    client=client,
    system_prompt=DATA_SCIENTIST_SYSTEM_PROMPT,
    tools=[code_interpreter],
)

tech_lead_agent.can_call([data_engineer_agent, data_scientist_agent])

while True:
    user_input = input("Input: ")
    if user_input.lower() == "quit":
        break
    response = tech_lead_agent.run(user_input)
    print(response.text)
