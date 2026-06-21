"""
Research Desk — Week 3 Project
===============================
Class hierarchy:
  Agent       — brain: chat(), _run_loop(), dispatch(), sessions
  REPLAgent   — terminal REPL + one-shot CLI
  TUIAgent    — Textual UI (in tui.py)

Usage:
  python agent.py                              # REPLAgent.run()
  python agent.py "What is quantum computing?" # REPLAgent.run_once()
  python agent.py --tui                        # TUIAgent.run()
  python agent.py --session abc123 "continue"
"""
import os
import json
import argparse
from openai import OpenAI

# Import our custom modules
import sessions as memory
from tools import ALL_TOOLS, TOOL_FUNCTIONS

# Initialize OpenRouter Client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

# Use the free model
MODEL = "openrouter/free" 

class Agent:
    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or memory.create_session()
        
        try:
            history_data = memory.load_session(self.session_id)
            self.messages = history_data.get("messages", [])
            # NEW: Load the title from memory!
            self.title = history_data.get("title", "Untitled") 
        except FileNotFoundError:
            system_prompt = memory.build_system_prompt()
            self.messages = [{"role": "system", "content": system_prompt}]
            self.title = "Untitled"
            # NEW: Pass the title when saving
            memory.save_session(self.session_id, self.messages, title=self.title)

    def _generate_title(self, first_message: str) -> str:
        """NEW: A mini-brain function just for generating nice titles."""
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": f"Write a 3 to 5 word title for this prompt. Return ONLY the title, no quotes, no punctuation: {first_message}"}],
                max_tokens=15
            )
            return response.choices[0].message.content.strip()
        except:
            return "New Research Session"

    def chat(self, user_message: str) -> str:
        # NEW: If this is the first message, generate a title!
        if self.title == "Untitled":
            self.title = self._generate_title(user_message)

        self.messages.append({"role": "user", "content": user_message})
        memory.save_session(self.session_id, self.messages, title=self.title)
        return self._run_loop()

    def _run_loop(self) -> str:
        MAX_ITERATIONS = 10
        for _ in range(MAX_ITERATIONS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=ALL_TOOLS
            )
            
            message = response.choices[0].message
            self.messages.append(message.model_dump(exclude_none=True))
            memory.save_session(self.session_id, self.messages, title=self.title)

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result = self.dispatch(tool_call)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                    memory.save_session(self.session_id, self.messages, title=self.title)
            else:
                return message.content
                
        return "Error: Maximum thinking iterations reached."

    def dispatch(self, tool_call) -> dict:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        
        self._emit("tool_start", name=name, args=args)
        
        if name in TOOL_FUNCTIONS:
            try:
                result = TOOL_FUNCTIONS[name](**args)
                self._emit("tool_end", name=name, result=result)
                return result
            except Exception as e:
                self._emit("tool_error", name=name, error=str(e))
                return {"error": str(e)}
                
        return {"error": f"Tool {name} not found"}

    def _emit(self, event: str, **data) -> None:
        """Log tool executions to a permanent, per-session file."""
        log_entry = ""
        if event == "tool_start":
            log_entry = f"START: {data.get('name')} with args: {data.get('args')}\n"
        elif event == "tool_end":
            log_entry = f"END: {data.get('name')} | Result length: {len(str(data.get('result', '')))} chars\n"
        elif event == "tool_error":
            log_entry = f"ERROR: {data.get('name')} | {data.get('error')}\n"
            
        if log_entry:
            # Dynamically name the file based on the session ID
            # We save it inside the .agent/ folder to keep your root directory clean
            log_filename = f".agent/{self.session_id}_tools.log"
            
            with open(log_filename, "a", encoding="utf-8") as f:
                f.write(log_entry)

    def run_once(self, prompt: str) -> str:
        return self.chat(prompt)


class REPLAgent(Agent):
    """Standard terminal interface with System Commands."""
    
    def _emit(self, event: str, **data) -> None:
        # 1. Print to the terminal screen
        if event == "tool_start":
            print(f"  [⚡ Executing Tool] {data['name']}")
        # 2. Trigger the base Agent logger we just built to save it to the file
        super()._emit(event, **data)

    def run(self):
        print(f"Research Desk [Session: {self.session_id}] — Type /quit to exit")
        while True:
            try:
                user_input = input("\n> ").strip()
                
                # Command: Quit
                if user_input == "/quit":
                    break
                    
                # Command: List Sessions
                elif user_input == "/sessions":
                    sessions = memory.list_sessions()
                    print("\n--- Saved Sessions ---")
                    for s in sessions:
                        print(f"ID: {s['id']} | Title: {s['title']}")
                    continue
                    
                # Command: Resume specific session
                elif user_input.startswith("/resume "):
                    new_id = user_input.split(" ")[1]
                    try:
                        history = memory.load_session(new_id)
                        self.session_id = new_id
                        self.messages = history.get("messages", [])
                        self.title = history.get("title", "Untitled")
                        print(f"\n✅ Resumed session: {self.title} ({new_id})")
                    except FileNotFoundError:
                        print(f"\n❌ Session '{new_id}' not found.")
                    continue
                
                # Ignore empty inputs
                elif not user_input:
                    continue
                
                # Normal Chat routing
                print(f"\nAgent: {self.chat(user_input)}")
                
            except (KeyboardInterrupt, EOFError):
                break

def get_last_session():
    """Look at all saved files and pick the most recent one automatically."""
    all_sessions = memory.list_sessions()
    if all_sessions:
        return all_sessions[0]["id"] # list_sessions puts the newest one at index 0!
    return None

def main():
    parser = argparse.ArgumentParser(description="Research Desk Agent")
    parser.add_argument("query", nargs="*", help="Run a one-shot CLI query")
    parser.add_argument("--tui", action="store_true", help="Launch the Textual UI")
    parser.add_argument("--session", type=str, help="Load a specific session ID")
    args = parser.parse_args()

    # Determine which memory to load
    session_to_use = args.session or get_last_session()

    # Launch the requested mode
    if args.tui:
        try:
            from tui import ResearchDeskApp, TUIAgent
            agent = TUIAgent(session_id=session_to_use)
            app = ResearchDeskApp(agent)
            agent.ui_callback = lambda msg: app.call_from_thread(app.log_tool, msg)
            app.run()
        except ImportError:
            print("Error: tui.py not found. Make sure it is saved in the same directory.")
    elif args.query:
        agent = REPLAgent(session_id=session_to_use)
        print(agent.run_once(" ".join(args.query)))
    else:
        agent = REPLAgent(session_id=session_to_use)
        agent.run()

if __name__ == "__main__":
    main()