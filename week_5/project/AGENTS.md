# Code Scout Rules

## Codebase Exploration Strategy
- **THE REPO MAP:** If the user asks you to implement a complex feature, fix a broad bug, or understand the architecture, your VERY FIRST step (after `add_todos`) should be to call `get_repo_map`. This will give you the "PageRank" of the most important files.
- **TARGETED SEARCH:** Once you have the Repo Map, use `grep` and `list_definitions` to narrow down exactly which files contain the specific functions you need to edit.
- **SKIP IF KNOWN:** If the user explicitly tells you which file to edit (e.g., "Add a print statement to agent.py"), do NOT run the Repo Map. Just go straight to `read_file`.

## Tools & File Operations
- Prefer `run_command` for git history, tests, and broad search (grep/find).
- Use `read_file` once you know the file and roughly which lines matter.
- Prefer `edit_file` over `run_command` for precise, line-level changes; use `run_command` for anything `edit_file` doesn't cover (like renaming files or multi-file sed replacements).
- Expect destructive or unclassified commands and any write/edit to pause for human approval — that is normal, not an error. If the user rejects an action, read their feedback and try a different approach.
- **DELEGATE EXPLORATION:** If you need to search through multiple files to understand a bug or find where a function is defined, use the `delegate_exploration` tool. Do not run dozens of `read_file` commands yourself; let the subagent do the digging and bring you back a summary digest.

## Planning & Todos
- **MANDATORY PLANNING:** You MUST call `add_todos` at the very beginning of EVERY response to outline your steps before you call any other tools. Do not skip this.
- Update your todo list using `mark_todo` as items complete — do not batch updates to the end.
- **STRICT COMPLETION RULE:** A todo item that changes code is not "completed" until the relevant verification command (usually the test suite) has actually exited 0. You MUST provide the command in the `verification_command` parameter so the system can run it to prove your work.
- **FALLBACK VERIFICATION:** If there is no test suite, you must still verify your work. Use `run_command` to execute a smoke test (e.g., `python -c "import module; module.func()"`) or re-run the command that originally failed. Do not leave a task unverified.

## Citations & Search Strategy
- Always cite `file:line` for any claim about behavior.
- If `grep` or `run_command` returns zero results, try a broader search term before reporting that something doesn't exist.