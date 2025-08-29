import asyncio
from claude_code_sdk import (
    query,
    ClaudeCodeOptions,
    ToolUseBlock,
    TextBlock,
    ResultMessage,
    AssistantMessage,
)
import os, dotenv

# Load Environment Variables
# Make sure that ANTHROPIC_API_KEY is in .env
dotenv.load_dotenv()

SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")

KUMO_API_KEY = os.getenv("KUMO_API_KEY")

# Directory where csv files live locally
dataDir = "/Users/kumo_intern/Desktop/anthropic_notebook/insurance_dataset_short/"
currentDir = "/Users/kumo_intern/Desktop/anthropic_notebook/"

# Names of files are necessary
fileNames = "agents.csv, policies.csv, customers.csv, pets.csv, products.csv, properties.csv, vehicles.csv"

# Prompt containing workflow
prompt = f"""
Hello Claude! I'm working with insurance company to try and retain customers whose policies are about to expire.

I have our data in a bunch of different csv files available here:
{dataDir}
The files are called {fileNames}.
“Do not infer results without executing the corresponding tool.

I want you to execute a multi-step workflow. Make sure you do exactly what I ask, and do not create/do unnecessary things

1) First, access my Supabase tables and make a list of the customer_id's whose policies are going to expire within the next 30 days.
2) Then, predict the likelihood of each of these customer_id's to renew their policies within the next 60 days.
3) For the customer_id's most likely to renew, predict what insurance policy they might be most interested in purchasing next.
4) Then, generate emails for each of these customers offering discounts for their current policy to encourage them to renew, and
    offer them a bundling discount for their current insurance, as well as the insurance they are most likely to buy next. Make sure the emails
    don't seem spammy- keep them concise and professional, avoiding whimsical things like emojis. Store these in a JSON file called emails.json, and put that
    in this current directory, which is {currentDir}. That is the only output
    that you should create.
"""


async def main():
    # Initialize the mcp_servers for claude
    mcp_servers = {
        # Supabase MCP
        "supabase": {
            "command": "npx",
            "args": [
                "-y",
                "@supabase/mcp-server-supabase@latest",
                "--read-only",
                f"--project-ref={SUPABASE_PROJECT_ID}",
            ],
            "env": {"SUPABASE_ACCESS_TOKEN": f"{SUPABASE_ACCESS_TOKEN}"},
        },
        # KumoRFM MCP
        "kumo-rfm": {
            # Path to directory where python executable for kumo-rfm-mcp lives
            "command": "/Users/kumo_intern/Documents/GitHub/kumo-rfm-mcp/.venv/bin/python",
            "args": ["-m", "kumo_rfm_mcp.server"],
            "env": {
                "KUMO_API_KEY": f"{KUMO_API_KEY}",
                "KUMO_API_URL": "https://kumorfm.ai/api",
            },
        },
    }

    # Parse every message in query with given prompt
    async for message in query(
        prompt=prompt,
        # Initialize options
        options=ClaudeCodeOptions(
            mcp_servers=mcp_servers,
            system_prompt="You are a helpful assistant that helps insurance companies forecast customer retention using the tools available to you.",
            max_turns=None,  # Unlimited amount of turns
            permission_mode="bypassPermissions",  # Bypass permissions for local MCP servers (use with caution)
        ),
    ):

        if isinstance(message, AssistantMessage):
            for block in message.content:
                # If a tool is used, print it
                if isinstance(block, ToolUseBlock):
                    print(f"[Tool: {block.name}]")
                elif isinstance(block, TextBlock):
                    print(block.text, flush=True)

        # Print the final cost at the end
        elif isinstance(message, ResultMessage):
            cost = getattr(message, "total_cost_usd", None)
            if cost is not None:
                print(f"\n\nReview complete. Total cost: ${cost:.4f}")


asyncio.run(main())
