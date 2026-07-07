#!/usr/bin/env python3
import argparse
import subprocess
import sys

ALLOWED_TYPES = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]

def main():
    parser = argparse.ArgumentParser(description="Enforces Conventional Commits.")
    parser.add_argument("--type", required=True, choices=ALLOWED_TYPES, help="The type of commit.")
    parser.add_argument("--scope", type=str, default="", help="Optional scope (e.g., auth, parser).")
    parser.add_argument("--message", required=True, type=str, help="The short description of the change.")
    
    args = parser.parse_args()
    
    # Construct the commit message
    scope_str = f"({args.scope})" if args.scope else ""
    commit_message = f"{args.type}{scope_str}: {args.message.lower()}"
    
    print(f"Executing: git commit -m '{commit_message}'")
    
    # Run the git command
    try:
        result = subprocess.run(
            ["git", "commit", "-m", commit_message], 
            capture_output=True, text=True, check=True
        )
        print("✅ Commit successful!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("❌ Commit failed. Did you forget to run 'git add' first?")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()