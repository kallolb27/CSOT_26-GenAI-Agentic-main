"""
config.py
=========
Global configuration and path management for the Coding Agent.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# 1. Base Workspace Resolution
WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))

# 2. Agent State Isolation Directory
AGENT_DIR= os.path.dirname(os.path.abspath(__file__))
os.makedirs(AGENT_DIR, exist_ok=True)  # Ensures the directory always exists safely

# 3. Create the hidden .agent directory safely
AGENT_STATE_DIR = os.path.join(AGENT_DIR, ".agent")
os.makedirs(AGENT_STATE_DIR, exist_ok=True) 

# 4. State Management Files
TODO_FILE = os.path.join(AGENT_STATE_DIR, ".agent_todos.json")