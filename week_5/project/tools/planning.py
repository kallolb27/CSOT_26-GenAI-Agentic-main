"""
tools/planning.py
=================
State and Todo management tools to handle multi-step planning and accountability.
"""

import json
import os

# Look here! We import the exact file path from our central config
from config import TODO_FILE
# NEW: Import the command runner so we can test the AI's work
from tools.system import run_command

# --- 1. Storage Helpers ---

def _load_todos() -> list:
    """Reads the todo file, returning an empty list if it doesn't exist."""
    if not os.path.exists(TODO_FILE):
        return []
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def _save_todos(todos: list):
    """Writes the todo list back to disk."""
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2)

# --- 2. Core Functions ---

def add_todos(tasks: list) -> dict:
    """
    Accepts a list of dictionaries containing 'task' and 'verification_method'.
    Auto-assigns IDs and sets default pending status.
    """
    todos = _load_todos()
    start_id = len(todos) + 1
    added_count = 0
    
    for i, t in enumerate(tasks):
        new_todo = {
            "id": str(start_id + i),
            "task": t.get("task", "Unknown Task"),
            "verification_method": t.get("verification_method", "None provided"),
            "status": "pending",
            "verification_result": None,
            "blocked_reason": None
        }
        todos.append(new_todo)
        added_count += 1
        
    _save_todos(todos)
    return {"message": f"Successfully added {added_count} todos.", "current_list": todos}

def get_todos() -> dict:
    """Returns the current todo list."""
    todos = _load_todos()
    if not todos:
        return {"message": "The todo list is currently empty."}
    return {"todos": todos}

def mark_todo(
    todo_id: str, 
    status: str, 
    verification_command: str = None, 
    blocked_reason: str = None
) -> dict:
    """Updates a todo, strictly running the verification command to prove completion."""
    todos = _load_todos()
    valid_statuses = ["pending", "in_progress", "completed", "blocked"]
    
    if status not in valid_statuses:
        return {"error": f"Invalid status. Must be one of: {valid_statuses}"}

    for todo in todos:
        if todo["id"] == str(todo_id):
            
            # --- THE SYSTEM-EVALUATED VERIFICATION BLOCK ---
            if status == "completed":
                if not verification_command or verification_command.strip() == "":
                    return {"error": "REJECTED: You must provide a 'verification_command' (e.g., 'pytest') so the system can verify your work."}
                
                print(f"\n[System Taskmaster] Verifying task {todo_id} by running: {verification_command}")
                
                # Execute the AI's provided command using our secure runner
                result = run_command(verification_command)
                
                if "error" in result:
                    return {"error": f"Verification command was blocked or timed out: {result['error']}"}
                    
                if result.get("exit_code") != 0:
                    return {
                        "error": f"REJECTED: Task failed verification. Command exited with code {result.get('exit_code')}. Read the output and fix the code.",
                        "stdout": result.get("stdout"),
                        "stderr": result.get("stderr")
                    }
                
                # If it passes, save the proof internally
                todo["verification_result"] = f"Command passed: {verification_command}\nOutput: {result.get('stdout')[:100]}..."
                
            # --- THE BLOCKED ESCALATION ---
            elif status == "blocked":
                if not blocked_reason or blocked_reason.strip() == "":
                    return {"error": "REJECTED: You must provide a 'blocked_reason' so the human knows how to help."}
                todo["blocked_reason"] = blocked_reason
                
            # If rules pass, update the status and save
            todo["status"] = status
            _save_todos(todos)
            return {"message": f"Todo {todo_id} successfully updated to {status}.", "updated_todo": todo}
            
    return {"error": f"Todo with id '{todo_id}' not found."}


# --- 3. The Tool Schemas ---

PLANNING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_todos",
            "description": "Add new tasks to your todo list. Break complex goals down into smaller, verifiable steps. ALWAYS define a strict verification_method for how you will prove the task succeeded.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string", "description": "The goal of the task."},
                                "verification_method": {"type": "string", "description": "How you will verify this is complete (e.g., 'Run pytest tests/test_db.py')."}
                            },
                            "required": ["task", "verification_method"]
                        }
                    }
                },
                "required": ["tasks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_todos",
            "description": "Read the current state of your todo list.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_todo",
            "description": "Update the status of a specific task. If marking 'completed', you MUST provide a 'verification_command' that exits with 0. If marking 'blocked', you MUST provide a blocked_reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "string", "description": "The ID of the task to update."},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "blocked"]},
                    "verification_command": {"type": "string", "description": "REQUIRED if status is 'completed'. The exact terminal command to run (e.g., 'pytest tests/test_db.py'). The system will run this; it MUST exit 0 for the task to be marked complete."},
                    "blocked_reason": {"type": "string", "description": "REQUIRED if status is 'blocked'. Explain exactly why you are stuck so the user can assist."}
                },
                "required": ["todo_id", "status"]
            }
        }
    }
]