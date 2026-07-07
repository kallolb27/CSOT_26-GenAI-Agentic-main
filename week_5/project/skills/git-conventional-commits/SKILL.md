---
name: git-conventional-commits
description: Strict formatting rules and execution scripts for writing professional Git commit messages.
tags: git, version-control, workflow
---

# Git Conventional Commits Protocol

When you are asked to commit code, you MUST follow the Conventional Commits specification.

**Allowed Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

## Execution Protocol
Do NOT use the standard `git commit` command. You must use the bundled helper script to ensure strict formatting compliance.

1. First, stage your files using your `run_command` tool (e.g., `git add <file>`).
2. Then, use `run_command` to execute the bundled script:
   `python skills/git-conventional-commits/scripts/make_commit.py --type <type> [--scope <scope>] --message "<description>"`

**Example:**
`python skills/git-conventional-commits/scripts/make_commit.py --type feat --scope auth --message "add jwt login endpoint"`

## Need more info?
If you are unsure about scoping rules or grammar, use your `read_file` tool to read the bundled `reference/best_practices.md` file before proceeding.