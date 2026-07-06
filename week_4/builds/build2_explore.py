"""
Build 2: Finding Code (grep + AST Outline)
=============================================
Two tools for finding the right place in a codebase you've never seen:
search file contents by pattern, and get a structural outline of a
single file without reading the whole thing.

Tasks:
  1. resolve_path(path) -> str | None
  2. grep(pattern, path=".", case_sensitive=False, max_results=50) -> dict
  3. list_definitions(path) -> dict   — AST-aware: list every function/class
     declared in a Python file, with line numbers
  4. Wire grep + list_definitions into TOOLS

Real-world reference for #3: Aider's repo map does this across an entire
multi-language repo using tree-sitter "tag" queries (see
https://aider.chat/2023/10/22/repomap.html and the implementation at
https://github.com/Aider-AI/aider/blob/main/aider/repomap.py), then ranks
files by reference count with PageRank. That's the bonus-tier "repo map"
challenge (see the README) — list_definitions here is the Python-only,
stdlib-`ast`-based version, scoped to one file at a time. See
https://docs.python.org/3/library/ast.html for the module reference;
every `ast.FunctionDef`/`ast.AsyncFunctionDef`/`ast.ClassDef` node carries
`.name`, `.lineno`, and `.end_lineno` once parsed.

Test this against a real external repo, not this file's own directory —
clone something like https://github.com/pallets/flask into ../target_repo
and point WORKSPACE_ROOT at it before running the demo below.

Run directly: grep for a common pattern, then outline the first match.
"""

import ast
import os
import re

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_GREP_RESULTS = 50
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def resolve_path(path: str) -> str | None:
    """Resolve `path` inside WORKSPACE_ROOT; return None if it escapes."""
    abs_workspace = os.path.abspath(WORKSPACE_ROOT)
    full_path = os.path.abspath(os.path.join(abs_workspace, path))
    
    # The Breach Check: return None instead of crashing
    if not full_path.startswith(abs_workspace):
        return None
        
    return full_path


def grep(
    pattern: str,
    path: str = ".",
    case_sensitive: bool = False,
    max_results: int = MAX_GREP_RESULTS,
) -> dict:
    """
    Search file contents for `pattern` under `path`.
    Returns structured JSON with exact files, lines, and text.
    """
    safe_path = resolve_path(path)
    if not safe_path:
        return {"error": f"Path {path} is outside the workspace sandbox."}

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        search_regex = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid regex pattern: {e}"}

    matches = []
    total_matches = 0

    for root, dirs, files in os.walk(safe_path):
        # Prune excluded directories in-place so os.walk skips them entirely
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file_name in files:
            file_path = os.path.join(root, file_name)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_number, line in enumerate(f, start=1):
                        if search_regex.search(line):
                            total_matches += 1
                            if len(matches) < max_results:
                                matches.append({
                                    "file": os.path.relpath(file_path, WORKSPACE_ROOT),
                                    "line": line_number,
                                    "text": line.strip()
                                })
            except UnicodeDecodeError:
                # Skip binary files
                continue
            except Exception:
                # Skip unreadable files
                continue

    return {
        "matches": matches,
        "truncated": total_matches > max_results,
        "total_matches": total_matches
    }


def list_definitions(path: str) -> dict:
    """
    Parse a Python file with `ast` and return every function/class it
    declares, in source order, with line numbers.
    """
    safe_path = resolve_path(path)
    if not safe_path:
        return {"error": f"Path {path} is outside the workspace sandbox."}

    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": f"Could not read file: {e}"}

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"SyntaxError in {path}: {e}. The AI must fix the syntax before outlining."}

    definitions = []

    for node in tree.body:
        # Check for standalone functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "async function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            definitions.append({
                "kind": kind,
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno)
            })
            
        # Check for Classes and nested methods
        elif isinstance(node, ast.ClassDef):
            definitions.append({
                "kind": "class",
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno)
            })
            
            # Step inside the class body to find methods
            for class_node in node.body:
                if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    definitions.append({
                        "kind": "method",
                        "name": f"{node.name}.{class_node.name}", 
                        "line": class_node.lineno,
                        "end_line": getattr(class_node, "end_lineno", class_node.lineno)
                    })

    return {"definitions": definitions}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Search file contents for a pattern across the workspace. "
                "Use this before read_file when you don't already know which "
                "file you need."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Text or regex to search for."},
                    "path": {"type": "string", "description": "Subdirectory to search, default workspace root."},
                    "case_sensitive": {"type": "boolean", "description": "Default false."},
                    "max_results": {
                        "type": "integer",
                        "description": f"Cap on matches returned. Default {MAX_GREP_RESULTS}.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_definitions",
            "description": (
                "List the functions and classes declared in a Python file, "
                "with line numbers, without reading the whole file. Use this "
                "right after grep to decide which match is worth reading in "
                "full with read_file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to a Python file."},
                },
                "required": ["path"],
            },
        },
    },
]


if __name__ == "__main__":
    import json
    
    print("--- Testing grep ---")
    print("Searching for top-level function definitions ('def '):")
    grep_result = grep("def ", max_results=5)
    print(json.dumps(grep_result, indent=2))

    if grep_result.get("matches"):
        first_file = grep_result["matches"][0]["file"]
        print(f"\n--- Testing list_definitions on {first_file} ---")
        outline_result = list_definitions(first_file)
        print(json.dumps(outline_result, indent=2))