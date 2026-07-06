"""
tools/explore_agent.py
======================
A delegated read-only subagent that explores the codebase and returns a digest,
saving the main agent's context window from search clutter.
"""

import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# Import the actual functions the subagent is allowed to use
from tools.files import read_file, list_files
from tools.system import run_command

# Import schemas to build the subagent's limited toolbox
from tools.files import FILE_TOOLS
from tools.system import SYSTEM_TOOLS

load_dotenv()

# We will use the same OpenRouter setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)
MODEL = "openrouter/free" 

# 1. Build the Restricted Toolset
SUBAGENT_TOOLS = []
# Only allow read-only file tools
for tool in FILE_TOOLS:
    if tool["function"]["name"] in ["read_file", "list_files"]:
        SUBAGENT_TOOLS.append(tool)
# run_command is allowed because the human [y/N] gate protects it anyway
SUBAGENT_TOOLS.extend(SYSTEM_TOOLS)


# 2. The Subagent Core Loop
def delegate_exploration(task: str) -> dict:
    """Spins up a subagent to investigate a codebase issue and return a summary."""
    print(f"\n🕵️‍♂️ [Subagent] Booting up for task: {task}")
    
    system_prompt = (
        "You are a read-only investigation subagent. Your job is to explore the codebase "
        "to answer the orchestrator's question. You have access to list_files, read_file, "
        "and run_command. \n"
        "RULES:\n"
        "1. DO NOT try to edit files or write code. You are strictly read-only.\n"
        "2. When you find the answer, return a concise digest with explicit file:line citations.\n"
        "3. If you cannot find the answer after a few tries, summarize what you checked."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    
    MAX_TURNS = 5  # Hard cap to prevent runaway loops
    
    for turn in range(MAX_TURNS):
        print(f"🕵️‍♂️ [Subagent] Thinking (Turn {turn + 1}/{MAX_TURNS})...")
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=SUBAGENT_TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            return {"error": f"Subagent API crashed: {str(e)}"}
        finally:
                # --- RATE LIMIT THROTTLE ---
                # Wait 4 seconds after every API call to guarantee staying under 20 RPM
                print("   ⏳ [Throttle] Sleeping 4 seconds to respect API rate limits...")
                time.sleep(4)
                # ---------------------------------
            
        message = response.choices[0].message
        
        # If the subagent doesn't call a tool, it means it generated the final digest
        if not message.tool_calls:
            print(f"🕵️‍♂️ [Subagent] Investigation complete. Returning digest.")
            return {"digest": message.content}
            
        messages.append(message)
        
        # Execute the subagent's tool calls
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name == "read_file":
                result = read_file(**args)
            elif func_name == "list_files":
                result = list_files(**args)
            elif func_name == "run_command":
                result = run_command(**args)
            else:
                result = {"error": f"Tool '{func_name}' is not allowed for the subagent."}
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": func_name,
                "content": json.dumps(result)
            })
            
    return {"error": f"Subagent timed out after {MAX_TURNS} turns without finding the answer."}

# 3. The Schema to expose this tool to the Main Agent
EXPLORE_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "delegate_exploration",
            "description": "Dispatch a read-only subagent to search the codebase and find the root cause of an issue. Use this to save your own context window from getting cluttered with search results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Specific instruction for the subagent (e.g., 'Find why test_auth.py is failing and cite the line numbers')."}
                },
                "required": ["task"]
            }
        }
    }
]