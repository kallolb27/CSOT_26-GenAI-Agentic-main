"""
tools/system.py
===============
System-level tools for executing shell commands safely within the workspace.
Includes Human-in-the-Loop approval for write/delete actions.
"""

import os
import shlex
import subprocess

# Look here! We import the root directly from our new config file.
from config import WORKSPACE_ROOT

TIMEOUT_DEFAULT = 10
MAX_OUTPUT_CHARS = 8_000

# Known-safe: run immediately once the path check passes.
READ_ONLY_PREFIXES = (
    "grep", "find", "ls", "cat", "head", "tail", "wc",
    "git log", "git diff", "git status", "git blame", "git show",
    "pytest", "python -m pytest", "ruff", "flake8", "mypy",
)

# Known-destructive: always ask, even if they'd otherwise look harmless.
DESTRUCTIVE_PATTERNS = (
    "rm ", "mv ", ">", ">>", "git commit", "git push", "git checkout --",
    "pip install", "npm install", "curl ", "sudo ", "chmod ",
)

def paths_within_sandbox(command: str, workspace_root: str) -> bool:
    """Token-level check: no path-looking argument may resolve outside workspace."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False

    abs_workspace = os.path.abspath(workspace_root)

    for token in tokens:
        if "/" in token or "\\" in token or token == ".." or token.startswith("."):
            test_path = os.path.abspath(os.path.join(abs_workspace, token))
            if not test_path.startswith(abs_workspace):
                return False

    return True

def classify_command(command: str) -> str:
    """Return 'read_only' if safe, otherwise 'ask' for human approval."""
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in command:
            return "ask"

    for prefix in READ_ONLY_PREFIXES:
        if command.startswith(prefix):
            return "read_only"

    return "ask"

def run_command(command: str, cwd: str = None, timeout: int = TIMEOUT_DEFAULT) -> dict:
    """Run a shell command, sandboxed to `cwd` with human approval for modifications."""
    if cwd is None:
        cwd = WORKSPACE_ROOT

    # Line of Defense 1: Sandbox Check
    if not paths_within_sandbox(command, cwd):
        return {"error": "blocked: command references a path outside the workspace"}

    # Line of Defense 2: Classification Gate
    classification = classify_command(command)

    if classification == "ask":
        print("\n⚠️ WARNING: The agent wants to run a command that may write, delete, or install:")
        print(f"    {command}")
        approved = input("Allow this command? [y/N]: ").strip().lower() == "y"

        if not approved:
            return {"error": "blocked: user did not approve this command. Try a read-only alternative."}

    # Execution Phase
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )

        stdout_str = result.stdout
        is_truncated = False

        if len(stdout_str) > MAX_OUTPUT_CHARS:
            stdout_str = stdout_str[:MAX_OUTPUT_CHARS] + "\n...[OUTPUT TRUNCATED]..."
            is_truncated = True

        return {
            "stdout": stdout_str,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "truncated": is_truncated
        }

    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout} seconds."}
    except Exception as e:
        return {"error": f"System error executing command: {str(e)}"}


SYSTEM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command in the workspace and return its output. "
                "Use this to search (grep/find), inspect history (git log/diff), "
                "run tests, or make a change. Read-only commands run immediately. "
                "Anything that writes, deletes, or installs will pause and ask the "
                "human operator for approval — expect that pause, it's not a failure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Seconds before the command is killed. Default {TIMEOUT_DEFAULT}.",
                    },
                },
                "required": ["command"],
            },
        },
    }
]