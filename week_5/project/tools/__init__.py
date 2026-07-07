"""
tools/__init__.py
=================
The central switchboard for the Coding Agent. Aggregates all tool schemas 
and routes LLM tool calls to the correct underlying functions.
"""

# 1. Import the Tool Schemas
from .system import SYSTEM_TOOLS
from .explore import EXPLORE_TOOLS
from .planning import PLANNING_TOOLS
from .files import FILE_TOOLS
from tools.explore_agent import delegate_exploration, EXPLORE_AGENT_TOOLS
from .skills import SKILL_TOOLS

# 2. Import the underlying executable functions
from .system import run_command
from .explore import grep, list_definitions, get_repo_map
from .planning import add_todos, get_todos, mark_todo
from .files import read_file, write_file, edit_file, list_files
from .skills import load_skill

# --- The Master Tool Schema Array ---
# agent.py will import this single list and pass it to the LLM
TOOLS = SYSTEM_TOOLS + EXPLORE_TOOLS + PLANNING_TOOLS + FILE_TOOLS + EXPLORE_AGENT_TOOLS

def execute_tool(name: str, arguments: dict) -> dict:
    """
    The Master Dispatcher. Takes the tool name and arguments requested by the LLM, 
    routes them to the correct Python function, and returns the result.
    """
    try:
        # System Tools
        if name == "run_command":
            return run_command(**arguments)
            
        # Explore Tools
        elif name == "grep":
            return grep(**arguments)
        elif name == "list_definitions":
            return list_definitions(**arguments)
        elif name == "get_repo_map":
            return get_repo_map(**arguments)
            
        # Planning Tools
        elif name == "add_todos":
            return add_todos(**arguments)
        elif name == "get_todos":
            return get_todos() # get_todos takes no arguments
        elif name == "mark_todo":
            return mark_todo(**arguments)
            
        # File Tools
        elif name == "read_file":
            return read_file(**arguments)
        elif name == "write_file":
            return write_file(**arguments)
        elif name == "edit_file":
            return edit_file(**arguments)
        elif name == "list_files":
            return list_files(**arguments)
        
        # NEW: Subagent Tool
        elif name == "delegate_exploration":
            return delegate_exploration(**arguments)

        # Skill Tools
        elif name == "load_skill":
            return load_skill(**arguments)
            
        # Fallback for hallucinated tools
        else:
            return {"error": f"Tool '{name}' does not exist or is not registered in the dispatcher."}
            
    except TypeError as e:
        return {"error": f"Invalid arguments provided to {name}: {str(e)}"}
    except Exception as e:
        return {"error": f"Critical failure executing {name}: {str(e)}"}