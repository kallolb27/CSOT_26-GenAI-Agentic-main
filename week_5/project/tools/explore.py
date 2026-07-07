"""
tools/explore.py
================
Codebase exploration tools: pattern matching (grep) and AST-based file outlining.
"""
from collections import defaultdict
import ast
import os
import re

# Import the centralized workspace root
from config import WORKSPACE_ROOT

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

def get_repo_map(limit: int = 30) -> dict:
    """
    Generate a PageRank-style map of the most referenced functions/classes 
    across the entire workspace.
    """
    safe_path = resolve_path(".")
    if not safe_path:
        return {"error": "Workspace sandbox error."}

    definitions = {} # Map function/class names to their file paths
    
    # PASS 1: Find all Python files and extract their definitions using AST
    python_files = []
    for root, dirs, files in os.walk(safe_path):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    for file_path in python_files:
        rel_path = os.path.relpath(file_path, WORKSPACE_ROOT)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    definitions[node.name] = rel_path
        except Exception:
            continue # Skip files with syntax errors

    # PASS 2: Count how many times each definition is referenced elsewhere
    reference_counts = defaultdict(int)
    
    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            for name in definitions.keys():
                # Fast string check before doing expensive whole-word regex
                if name in content:
                    # Count whole-word matches only
                    matches = len(re.findall(r'\b' + re.escape(name) + r'\b', content))
                    if matches > 0:
                        reference_counts[name] += matches
        except Exception:
            continue

    # PASS 3: Rank by popularity and format the output
    ranked = sorted(reference_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Group the top results by file
    file_map = defaultdict(list)
    for name, count in ranked[:limit]:
        file_map[definitions[name]].append(f"{name} (referenced {count} times)")

    # Build the final readable string
    output = ["🧠 REPO MAP (Top Referenced Entities):", "-" * 40]
    for file, defs in file_map.items():
        output.append(f"📄 {file}:")
        for d in defs:
            output.append(f"   - {d}")

    if len(output) == 2:
        return {"content": "No cross-references found in the repository."}

    return {"content": "\n".join(output)}

# --- Export the Tool Schema for this specific module ---

EXPLORE_TOOLS = [
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
    {
        "type": "function",
        "function": {
            "name": "get_repo_map",
            "description": (
                "Get an architectural overview of the entire codebase. Returns a ranked list "
                "of the most frequently used functions and classes, organized by file. "
                "Use this at the start of a project to understand how the files connect."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer", 
                        "description": "Max number of top functions to return (default 30)."
                    }
                },
                "required": []
            }
        }
    }
]