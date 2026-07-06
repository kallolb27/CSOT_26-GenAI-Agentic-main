"""
tools/files.py
==============
Sandboxed file operations for precise reading, writing, and surgical editing.
Includes diff generation and a Human-in-the-Loop approval gate for all modifications.
"""

import os
import glob as glob_module
import difflib  # NEW: For generating visual diffs

from config import WORKSPACE_ROOT

MAX_READ_CHARS = 12_000

# ANSI Color Codes for the terminal
RED = '\033[91m'
GREEN = '\033[92m'
CYAN = '\033[96m'
RESET = '\033[0m'

# --- Helper Functions for Safety and Diffing ---

def print_colored_diff(diff_text: str):
    """Parses a unified diff string and prints it with standard git colors."""
    for line in diff_text.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            # Green for added code
            print(f"{GREEN}{line}{RESET}")
        elif line.startswith('-') and not line.startswith('---'):
            # Red for removed code
            print(f"{RED}{line}{RESET}")
        elif line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            # Cyan for file headers and line numbers
            print(f"{CYAN}{line}{RESET}")
        else:
            # Default terminal color for unchanged context lines
            print(line)

def resolve_path(path: str) -> str:
    """Ensure the requested path is safely within the workspace sandbox."""
    full_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    if not full_path.startswith(WORKSPACE_ROOT):
        raise ValueError(f"Security Error: Path '{path}' escapes the workspace sandbox.")
    return full_path

def _generate_diff(original_lines: list, new_lines: list, filename: str) -> str:
    """Generate a standard unified diff string."""
    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "\n".join(diff)

def _request_human_approval(action_desc: str, diff_text: str) -> bool:
    """Pause execution, show the diff, and ask the human for permission."""
    print(f"\n⚠️ WARNING: The agent wants to {action_desc}:")
    if diff_text.strip():
        print("-" * 50)
        print_colored_diff(diff_text) # <--- USE THE NEW COLOR FUNCTION HERE
        print("-" * 50)
    else:
        print("  (No changes detected / File is empty)")
        
    approved = input("Allow this file modification? [y/N]: ").strip().lower() == "y"
    return approved

# --- Core File Tools ---

def read_file(path: str, start_line: int = 1, end_line: int = None) -> dict:
    """Read a specific window of lines from a file, returning numbered lines."""
    try:
        full_path = resolve_path(path)
        if not full_path:
            return {"error": f"Security block: {path} is outside the workspace."}
        if not os.path.exists(full_path):
            return {"error": f"File not found: {path}"}

        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        total_lines = len(lines)
        if end_line==None:
            end_line=total_lines
        start_idx = max(0, start_line - 1)
        end_idx = min(end_line, total_lines)
        
        snippet = lines[start_idx:end_idx]
        
        # Add line numbers for precise AI editing
        numbered_snippet = [f"{i + start_line}| {line}" for i, line in enumerate(snippet)]
        content = "\n".join(numbered_snippet)

        if len(content) > MAX_READ_CHARS:
            content = content[:MAX_READ_CHARS] + "\n...[truncated]"

        return {
            "content": content,
            "total_lines": total_lines,
            "has_more": end_idx < total_lines
        }
    except Exception as e:
        return {"error": str(e)}

def write_file(path: str, content: str) -> dict:
    """Create a new file or overwrite an existing one (Requires Approval)."""
    try:
        full_path = resolve_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # 1. Get original content for the diff
        original_lines = []
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                original_lines = f.read().splitlines()
                
        new_lines = content.splitlines()
        
        # 2. Generate Diff and Ask Approval
        diff_text = _generate_diff(original_lines, new_lines, path)
        if not _request_human_approval(f"write to / overwrite '{path}'", diff_text):
            return {"error": "blocked: user did not approve this write operation. Explain why it is necessary or try a different approach."}

        # 3. Execute
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"content": f"Successfully wrote to {path}"}
    except Exception as e:
        return {"error": str(e)}

def edit_file(path: str, operation: str, start_line: int, end_line: int | None = None, content: str | None = None) -> dict:
    """Surgically edit specific lines inside a file (Requires Approval)."""
    try:
        full_path = resolve_path(path)
        if not os.path.exists(full_path):
            return {"error": f"File not found: {path}"}
            
        with open(full_path, "r", encoding="utf-8") as f:
            original_lines = f.read().splitlines()
            
        # Create a copy to manipulate
        new_lines = original_lines.copy()
            
        start_idx = max(0, start_line - 1)
        end_idx = max(0, end_line - 1) if end_line else start_idx
        
        # 1. Perform the operation in memory
        if operation == "replace":
            insert_lines = content.splitlines() if content else []
            new_lines[start_idx:end_idx + 1] = insert_lines
            preview = f"Replaced lines {start_line}-{end_line}."
            
        elif operation == "delete":
            del new_lines[start_idx:end_idx + 1]
            preview = f"Deleted lines {start_line}-{end_line}."
            
        elif operation == "append":
            insert_lines = content.splitlines() if content else []
            new_lines = new_lines[:start_idx + 1] + insert_lines + new_lines[start_idx + 1:]
            preview = f"Appended {len(insert_lines)} lines after line {start_line}."
            
        else:
            return {"error": f"Unknown operation: {operation}"}
            
        # 2. Generate Diff and Ask Approval
        diff_text = _generate_diff(original_lines, new_lines, path)
        if not _request_human_approval(f"edit '{path}'", diff_text):
            return {"error": "blocked: user did not approve this edit. Check your line numbers and try again."}
            
        # 3. Execute
        with open(full_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
            
        return {
            "message": f"Success. {preview}",
            "diff_applied": diff_text
        }
    except Exception as e:
        return {"error": str(e)}

def list_files(path: str = ".", pattern: str = "*") -> dict:
    """List files in the workspace so the AI can navigate."""
    try:
        full_path = resolve_path(path)
        search_pattern = os.path.join(full_path, "**", pattern)
        files = glob_module.glob(search_pattern, recursive=True)
        rel_files = [os.path.relpath(f, WORKSPACE_ROOT) for f in files if os.path.isfile(f)]
        return {"content": "\n".join(rel_files) if rel_files else "No files found."}
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# TOOL SCHEMAS FOR THE AGENT
# ==========================================

FILE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write new content to a file. Used for creating brand new files. This triggers a human approval prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path in workspace."},
                    "content": {"type": "string", "description": "The file content to write."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read lines from a file. Returns numbered lines for accurate editing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "description": "Line to start reading from (1-indexed). Default 1."},
                    "read_lines": {"type": "integer", "description": "Number of lines to read. Default None."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit specific lines in a file. ALWAYS run read_file first to check line numbers. This triggers a human approval prompt showing your diff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {"type": "string", "enum": ["replace", "delete", "append"]},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string", "description": "New content for replace/append"}
                },
                "required": ["path", "operation", "start_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory to see what exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to search (default '.')"},
                    "pattern": {"type": "string", "description": "Glob pattern (default '*')"}
                },
                "required": []
            }
        }
    }
]