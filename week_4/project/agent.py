"""
agent.py
========
The core autonomous loop. Connects to OpenRouter, manages state, 
enforces the Todo list completion rules, and handles CLI sessions.
"""

import os
import json
import time
import argparse
from openai import OpenAI
from dotenv import load_dotenv

# 1. Import our custom tools and switchboard
from tools import TOOLS, execute_tool
from tools.planning import get_todos

# Import the newly upgraded memory module
import memory 

# 2. OpenRouter Configuration
load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

MODEL = os.getenv("OPENROUTER_MODEL", "cohere/north-mini-code:free")

# 3. Helper Functions
def load_system_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "AGENTS.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("⚠️ WARNING: AGENTS.md not found. Running without strict system instructions.")
        return "You are a helpful coding assistant."

def has_unfinished_todos() -> bool:
    """The Taskmaster Check: Looks at the JSON file to see if tasks are pending."""
    todo_state = get_todos()
    if "todos" not in todo_state:
        return False
        
    for task in todo_state["todos"]:
        if task.get("status") in ["pending", "in_progress"]:
            return True
    return False

# ==========================================
# CORE AGENT LOOP
# ==========================================
def execute_agent_turn(user_input: str, messages: list, session_id: str):
    """Handles a single complete turn of the agent's reasoning and tool usage."""
    
    messages.append({"role": "user", "content": user_input})
    memory.save_history(session_id, messages)

    while True:
        print("\n🤖 Agent is thinking...")
        
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            print(f"❌ API Error: {e}")
            break
        finally:
            # --- RATE LIMIT THROTTLE ---
            print("   ⏳ [Throttle] Sleeping 4 seconds to respect API rate limits...")
            time.sleep(4)

        message = response.choices[0].message
        
        # If the agent just wants to talk (no tools)
        if not message.tool_calls:
            
            # --- THE TASKMASTER INTERCEPT ---
            if has_unfinished_todos():
                print("\n🛑 [Taskmaster Intercept]: Agent attempted to finish turn, but has unfinished tasks.")
                intercept_message = (
                    "SYSTEM: You attempted to finish your response, but you still have tasks marked as 'pending' or 'in_progress' "
                    "on your todo list. You cannot stop working until all tasks are 'completed' or 'blocked'. "
                    "Use the 'get_todos' tool to review your tasks, and continue executing your plan."
                )
                messages.append({"role": "assistant", "content": message.content or ""})
                messages.append({"role": "user", "content": intercept_message})
                memory.save_history(session_id, messages)
                continue # Loop back to the API call!
            
            # If no tools AND no pending tasks, print the response and finish turn
            messages.append({"role": "assistant", "content": message.content})
            print(f"\n🤖 Code Scout: {message.content}")
            memory.save_history(session_id, messages)
            break 

        # 3. Handle Tool Calls
        messages.append(message.model_dump(exclude_none=True))
        memory.save_history(session_id, messages)
        
        # --- PLANNING GATEWAY ---
        has_planned = False
        for msg in messages:
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    if tc.get("function", {}).get("name") == "add_todos":
                        has_planned = True
                        break
            if has_planned:
                break
        
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            print(f"   🔧 Calling tool: {function_name}")
            
            # GATEWAY CHECK: Block if planning hasn't happened!
            if not has_planned and function_name != "add_todos":
                print(f"   🛑 [Gateway] Blocked tool '{function_name}'. Forcing agent to plan first.")
                result = {
                    "error": (
                        f"Protocol Violation: You attempted to call '{function_name}' "
                        f"without a plan. You MUST call 'add_todos' first to initialize "
                        f"the project milestones before running any other operations."
                    )
                }
            else:
                # Normal Execution Path
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    result = execute_tool(function_name, arguments)
                except json.JSONDecodeError:
                    result = {"error": "Failed to parse tool arguments as valid JSON."}
                except Exception as e:
                    result = {"error": f"Tool execution failed: {str(e)}"}
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(result)
            })
            memory.save_history(session_id, messages)


# ==========================================
# CLI ROUTING & INITIALIZATION
# ==========================================
def main():
    # Set up the CLI contract
    parser = argparse.ArgumentParser(description="Code Scout Autonomous Agent")
    parser.add_argument("task", nargs="?", type=str, help="A single task to execute in one-shot mode.")
    parser.add_argument("--session", type=str, help="Resume or start a specific session ID.")
    args = parser.parse_args()

    # 1. Determine Session ID
    is_new_session = False
    if args.session:
        session_id = args.session
    else:
        session_id = memory.create_session()
        is_new_session = True

    # 2. Initialize Memory
    messages = memory.load_history(session_id)

    if not messages:
        messages.append({"role": "system", "content": load_system_prompt()})
        memory.save_history(session_id, messages)
        if not is_new_session:
            print(f"🆕 Created new session file for ID: {session_id}")
    else:
        print(f"📦 [Memory] Loaded {len(messages)} previous messages for session '{session_id}'.")

    # 3. Route to One-Shot or REPL
    if args.task:
        # --- ONE-SHOT MODE ---
        print(f"🚀 Launching One-Shot Task: '{args.task}'")
        print(f"🔗 Session ID: {session_id}")
        print("-" * 50)
        execute_agent_turn(args.task, messages, session_id)
        print("\n✅ One-shot task complete. Exiting.")
        
    else:
        # --- REPL MODE ---
        print("🤖 Code Scout Agent Initialized (OpenRouter Backend)")
        print(f"🔗 Session ID: {session_id}")
        print(f"🧠 Active Model: {MODEL}")
        print("Type 'exit' or 'quit' to end the session.")
        print("Type '/sessions' to view all history, or '/clear' to wipe this session.\n")
        print("-" * 50)

        while True:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                print("Shutting down Code Scout...")
                break
                
            # Session Listing Command
            if user_input.lower() == '/sessions':
                sessions = memory.list_sessions()
                print("\n--- Saved Sessions ---")
                for s in sessions:
                    date_str = s['updated_at'][:16].replace('T', ' ')
                    print(f"ID: {s['id']} | Date: {date_str} | Title: {s['title']}")
                continue
                
            # Clear Command
            if user_input.lower() == '/clear':
                memory.clear_history(session_id)
                messages = [{"role": "system", "content": load_system_prompt()}]
                memory.save_history(session_id, messages)
                print(f"🧠 [Memory] Session '{session_id}' has been wiped clean. Starting fresh.")
                continue
                
            if not user_input:
                continue

            # Route input to the main reasoning loop
            execute_agent_turn(user_input, messages, session_id)

if __name__ == "__main__":
    main()