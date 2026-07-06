"""
Build 3: Todo Tools
======================
A todo list the model maintains itself — what it's planning to do, what
it's actually done, and how it'll know each item really worked.

This build is intentionally less prescriptive than Builds 1 and 2. You
decide the exact shape of a todo and how the list is stored — in memory,
in a dict, in a JSON file under .agent/, however you like. The one hard
requirement, from Lesson 2: every todo needs a short title, a
description, and a verification method — some concrete, checkable way
to know the item is actually done ("run pytest tests/test_auth.py and
confirm exit code 0"), not just a status flag the model sets on its own
say-so.

Tasks (design these yourself — the signatures below are a starting
point, not a contract you have to match):
  1. add_todos(...)  — add one or more todos to the list
  2. get_todos(...)  — return the current list, however you choose to
     filter or shape it
  3. mark_todo(...)  — update a todo's status
  4. Once you've settled on a shape, write the TOOLS schema yourself
     and wire it into the agent loop's stop condition (Lesson 2) — the
     loop shouldn't consider itself done while a todo is incomplete.

Questions to resolve before you write code — there's no single right
answer, but you should be able to defend whatever you pick:
  - What does "status" need to express? pending/in_progress/completed
    is Lesson 2's minimum — is that enough once verification enters
    the picture, or do you need something like "blocked" too?
  - Should mark_todo require evidence (e.g. a command's exit code)
    before it'll accept "completed," and refuse otherwise? Lesson 2's
    "Completed Should Mean Verified, Not Just Claimed" argues yes —
    decide how strict to make that in code.
  - Where does the list live, and what survives a resumed session
    (Week 3)? A module-level list won't survive a process restart;
    is that good enough for this build, or do you need it on disk?
  - Should add_todos take one todo or a whole plan at once? (Lesson 2's
    todo_write always sends the full current list back — you don't
    have to copy that design, but know why it might matter.)

Run directly once you've implemented something real: add a couple of
todos, mark one in_progress, try to mark it completed without evidence
and see whether your own rules let that happen, then get_todos() and
confirm the list reflects what you'd expect.
"""

"""
Build 3: Todo Tools
======================
A todo list the model maintains itself — what it's planning to do, what
it's actually done, and how it'll know each item really worked.
"""

import json
import os

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
TODO_FILE = os.path.join(WORKSPACE_ROOT, ".agent_todos.json")

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
    verification_result: str = None, 
    blocked_reason: str = None
) -> dict:
    """Updates a todo, strictly enforcing evidence for completion and reasons for blocks."""
    todos = _load_todos()
    valid_statuses = ["pending", "in_progress", "completed", "blocked"]
    
    if status not in valid_statuses:
        return {"error": f"Invalid status. Must be one of: {valid_statuses}"}

    for todo in todos:
        if todo["id"] == str(todo_id):
            
            # --- STRICT RULE 1: The Verification Block ---
            if status == "completed":
                if not verification_result or verification_result.strip() == "":
                    return {"error": "REJECTED: You cannot mark this complete without providing evidence in the 'verification_result' argument."}
                todo["verification_result"] = verification_result
                
            # --- STRICT RULE 2: The Blocked Escalation ---
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

TOOLS = [
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
            "description": "Update the status of a specific task. If marking 'completed', you MUST provide a verification_result. If marking 'blocked', you MUST provide a blocked_reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "string", "description": "The ID of the task to update."},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "blocked"]},
                    "verification_result": {"type": "string", "description": "REQUIRED if status is 'completed'. Provide evidence like terminal output or a file snippet proving it worked."},
                    "blocked_reason": {"type": "string", "description": "REQUIRED if status is 'blocked'. Explain exactly why you are stuck so the user can assist."}
                },
                "required": ["todo_id", "status"]
            }
        }
    }
]


# --- 4. Testing Block ---

if __name__ == "__main__":
    print("--- 1. Testing add_todos ---")
    add_result = add_todos([
        {"task": "Run tests", "verification_method": "Check for 0 failures"}
    ])
    print(add_result)

    print("\n--- 2. Testing Lazy AI (Should Fail) ---")
    lazy_result = mark_todo(todo_id="1", status="completed")
    print(lazy_result)

    print("\n--- 3. Testing Honest AI (Should Pass) ---")
    honest_result = mark_todo(
        todo_id="1", 
        status="completed", 
        verification_result="Ran pytest. 5 passed, 0 failed."
    )
    print(honest_result)
