"""
Build 1: Command Execution
============================
A sandboxed run_command tool: search, inspect history, run tests — and,
once a human approves, make real changes to the repo.

Tasks:
  1. paths_within_sandbox(command, workspace_root) -> bool
  2. classify_command(command) -> "read_only" | "ask"
  3. run_command(command, cwd=WORKSPACE_ROOT, timeout=10) -> dict
  4. Wire run_command into the OpenAI tool schema (TOOLS)

Run directly: a read-only command should run immediately; a destructive
one should print a warning and wait for y/n before doing anything.
"""

import os
import shlex
import subprocess

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
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
    """
    Token-level check: no path-looking argument in `command` may resolve
    outside `workspace_root`.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        # Fail closed on syntax errors (like mismatched quotes)
        return False

    abs_workspace = os.path.abspath(workspace_root)

    for token in tokens:
        if "/" in token or "\\" in token or token == ".." or token.startswith("."):
            test_path = os.path.abspath(os.path.join(abs_workspace, token))
            if not test_path.startswith(abs_workspace):
                return False

    return True


def classify_command(command: str) -> str:
    """
    Return "read_only" if `command` matches a known-safe prefix and no
    destructive pattern, otherwise "ask".
    """
    # Priority 1: Instant ask if a destructive pattern is found anywhere
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in command:
            return "ask"

    # Priority 2: Clear it if it starts with a known-safe prefix
    for prefix in READ_ONLY_PREFIXES:
        if command.startswith(prefix):
            return "read_only"

    # Priority 3: Fallback safety net
    return "ask"


def run_command(command: str, cwd: str = WORKSPACE_ROOT, timeout: int = TIMEOUT_DEFAULT) -> dict:
    """
    Run a shell command, sandboxed to `cwd`.
    """
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
            "stderr": result.stderr,  # Never truncate stderr
            "exit_code": result.returncode,
            "truncated": is_truncated
        }

    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout} seconds."}
    except Exception as e:
        return {"error": f"System error executing command: {str(e)}"}


TOOLS = [
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


if __name__ == "__main__":
    print("Testing Read-only command (should run immediately):")
    print(run_command("echo 'Hello World' | wc -w"))

    print("\nTesting Destructive command (should pause and ask for approval):")
    print(run_command("rm -rf /tmp/does-not-exist-example"))