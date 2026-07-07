"""
agent.py
========
The core autonomous loop. Connects to OpenRouter, manages state, 
enforces the Todo list completion rules, and handles CLI sessions.
"""

import os
import json
import time
import asyncio
import argparse
from openai import OpenAI
from dotenv import load_dotenv
from tools.mcp_client import MCPManager, load_mcp_config

# 1. Import our custom tools and switchboard
from tools import TOOLS, execute_tool
from tools.planning import get_todos

# Import the newly upgraded memory module
import memory 

from config import WORKSPACE_ROOT
from prompt_builder import build_system_prompt

# 2. OpenRouter Configuration
load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

MODEL = os.getenv("OPENROUTER_MODEL", "cohere/north-mini-code:free")

# 3. Helper Functions

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
async def execute_agent_turn(user_input: str, messages: list, session_id: str, mcp: MCPManager):
    """Handles a single complete turn of the agent's reasoning and tool usage."""
    
    messages.append({"role": "user", "content": user_input})
    memory.save_history(session_id, messages)
    all_tools = TOOLS + mcp.openai_tools

    while True:
        print("\n🤖 Agent is thinking...")
        
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=all_tools,
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

                    # 4. THE ROUTER: Check if this is an MCP tool or a local tool
                    if function_name in [t["function"]["name"] for t in mcp.openai_tools]:
                        print(f"   🌐 [MCP] Executing '{function_name}' remotely...")
                        mcp_result = await mcp.call_tool(function_name, arguments)
                        result = {"result": mcp_result}
                    else:
                        # It's a local tool (like read_file or run_command)
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
async def main():
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

    # 2. Prepare the MCP Manager (Instant Boot!)
    print("🔌 Loading Model Context Protocol (MCP) configs...")
    mcp = MCPManager()
    all_servers = load_mcp_config()
    active_mcp_names = []  # Start completely empty!
    # 2. Initialize Memory
    messages = memory.load_history(session_id)

    if not messages:
        dynamic_prompt = build_system_prompt(
            workspace_root=WORKSPACE_ROOT, 
            mcp_servers=active_mcp_names
        )
        messages.append({"role": "system", "content": dynamic_prompt})
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
        await execute_agent_turn(args.task, messages, session_id, mcp)
        print("\n✅ One-shot task complete. Exiting.")
        await mcp.aclose()  # 📞 Hang up the MCP connections gracefully!
        
    else:
        # --- REPL MODE ---
        print("🤖 Code Scout Agent Initialized (OpenRouter Backend)")
        print(f"🧠 Active Model: {MODEL}")
        print(f"🔗 Session ID: {session_id}")
        print("Type 'exit' or 'quit' to end the session.")
        print("💡 Type '/help' to see all available commands, skills, and MCP tools.")
        print("-" * 50)

        # --- INTERACTIVE REPL MODE ---
        while True:
            user_input = input("\n👤 You: ").strip()
            if not user_input:
                continue
                
            # Standard Exit Command (No slash required)
            if user_input.lower() in ["exit", "quit"]:
                print("Shutting down Code Scout...")
                await mcp.aclose()  # 📞 Hang up the MCP connections gracefully!
                break
                
            # --- THE CLI ROUTER (Bypasses the LLM entirely) ---
            if user_input.startswith("/"):
                parts = user_input.split()
                cmd = parts[0].lower()
                
                if cmd in ["/exit", "/quit"]:
                    print("Shutting down Code Scout...")
                    await mcp.aclose()
                    break
                    
                elif cmd == "/help":
                    print("\n🛠️ CODE SCOUT COMMANDS:")
                    print("  /skills              - List all available agent skills")
                    print("  /mcp list            - Show connected and available MCP servers")
                    print("  /mcp enable <name>   - Connect to a server mid-session")
                    print("  /mcp disable <name>  - Disconnect a server")
                    print("  /sessions            - View saved sessions")
                    print("  /clear               - Wipe current LLM context memory")
                    print("  exit / quit          - Shut down")

                elif cmd == "/skills":
                    print("\n📚 Installed Skills:")
                    print("  - python-pytest-tdd        : Strict TDD workflow & scaffolding")
                    print("  - react-nextjs-components  : App Router component standards")
                    print("  - git-conventional-commits : Formatting rules for Git commits")
                    
                elif cmd == "/mcp":
                    if len(parts) == 1:
                        print("\n⚠️ Usage: /mcp list | /mcp enable <name> | /mcp disable <name>")
                    
                    elif parts[1].lower() == "list":
                        print(f"\n📦 Available in config: {', '.join(all_servers.keys())}")
                        print(f"🔌 Currently Connected: {', '.join(active_mcp_names) if active_mcp_names else 'None'}")
                    
                    elif parts[1].lower() == "enable" and len(parts) > 2:
                        server_name = parts[2]
                        if server_name in active_mcp_names:
                            print(f"\n⚠️ {server_name} is already connected.")
                        elif server_name in all_servers:
                            await mcp.connect_server(server_name, all_servers[server_name])
                            active_mcp_names.append(server_name)
                            # Rebuild the prompt to tell the LLM it has new powers!
                            dynamic_prompt = build_system_prompt(
                                workspace_root=WORKSPACE_ROOT, 
                                mcp_servers=active_mcp_names
                            )
                            messages[0] = {"role": "system", "content": dynamic_prompt}
                        else:
                            print(f"\n⚠️ Server '{server_name}' not found in config.json")
                            
                    elif parts[1].lower() == "disable" and len(parts) > 2:
                        server_name = parts[2]
                        if server_name in active_mcp_names:
                            mcp.disconnect_server(server_name)
                            active_mcp_names.remove(server_name)
                            # Rebuild the prompt to remove the tools from the LLM's brain
                            dynamic_prompt = build_system_prompt(
                                workspace_root=WORKSPACE_ROOT, 
                                mcp_servers=active_mcp_names
                            )
                            messages[0] = {"role": "system", "content": dynamic_prompt}
                        else:
                            print(f"\n⚠️ Server '{server_name}' is not currently connected.")
                        
                elif cmd == "/sessions":
                    sessions = memory.list_sessions()
                    print("\n--- Saved Sessions ---")
                    for s in sessions:
                        date_str = s['updated_at'][:16].replace('T', ' ')
                        print(f"ID: {s['id']} | Date: {date_str} | Title: {s['title']}")
                        
                elif cmd == "/clear":
                    memory.clear_history(session_id)
                    # Rebuild the dynamic prompt to retain core instructions
                    dynamic_prompt = build_system_prompt(
                        workspace_root=WORKSPACE_ROOT, 
                        mcp_servers=active_mcp_names
                    )
                    messages = [{"role": "system", "content": dynamic_prompt}]
                    memory.save_history(session_id, messages)
                    print(f"🧠 [Memory] Session '{session_id}' has been wiped clean. Starting fresh.")
                    
                else:
                    print(f"\n⚠️ Unknown command: {cmd}. Try /help")
                
                # Critical: Skip the LLM execution for slash commands so we don't waste API calls
                continue 

            # --- NORMAL LLM EXECUTION ---
            # Route standard input to the main reasoning loop
            await execute_agent_turn(user_input, messages, session_id, mcp)

if __name__ == "__main__":
    asyncio.run(main())