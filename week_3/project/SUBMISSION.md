# Research Desk: Agentic AI Workspace
**Week 3 Final Submission**

## Overview
Research Desk is a fully functional, terminal-based AI research assistant. It leverages an autonomous LLM loop to execute multi-step research tasks, maintain persistent memory across sessions, interact with the local file system within a secure sandbox, and scrape live data from the internet and academic databases. 

The application features a split-pane **Textual User Interface (TUI)** that separates human-agent chat from backend tool execution logs, providing a transparent and professional user experience.

---

## 🧠 System Architecture: The Agent Loop
The core of the application relies on an autonomous reasoning loop defined in `_run_loop()`. Here is how the message flow and dispatch system operates:

1. **Prompt Injection:** The user's input is appended to the `messages` array and sent to the LLM.
2. **Evaluation & Tool Calling:** The LLM evaluates the prompt against its system instructions. If it determines a tool is needed, it returns a `tool_calls` object instead of a standard text response.
3. **The Dispatcher:** The script intercepts this response. The `dispatch()` function parses the JSON arguments provided by the LLM and maps the requested tool name to the actual Python function (e.g., mapping `"read_file"` to `files.read_file()`).
4. **Execution & Feedback:** The Python function executes, and its output (or error message) is packaged into a `"tool"` role message and appended to the history. 
5. **Looping & Termination:** The updated history is sent *back* to the LLM so it can read the tool's output. This loop continues until one of two termination conditions is met:
    * **Success:** The LLM decides it has enough information and returns a final text response to the user.
    * **Safety Limit:** The loop hits the `MAX_ITERATIONS` limit (set to 10) to prevent infinite loops and API token drain.

---

## 🏗️ Design Decisions
**1. Hugging Face Papers API vs. Raw arXiv XML**
When building the academic research tools (`papers.py`), I actively chose to integrate the Hugging Face Papers API rather than parsing arXiv directly. The HF API provides a much cleaner REST interface, normalizes paper IDs automatically across different repositories, and handles rate-limiting far more gracefully. This resulted in fewer crash errors for the agent when fetching massive academic documents.

**2. Isolated vs. Global Audit Logging**
When implementing the tool execution logger, I chose to generate dynamically named, per-session log files (e.g., `36db57db_tools.log`) stored inside the hidden `.agent/` directory, rather than a single global `agent.log` file. This prevents audit trails from becoming massive, unreadable dumps and perfectly organizes the agent's actions by project context.

---

## 🚧 Challenges & Reflections
**Challenge: Path Hallucination & Sandbox Escapes**
Early in the file tool implementation, the LLM would occasionally hallucinate absolute paths or attempt to read files outside the designated workspace (e.g., trying to read `../system_config`). 
**Solution:** I implemented strict path resolution and boundary enforcement inside `files.py`. Every requested path is now run through `os.path.abspath()` and verified to ensure it strictly starts with the designated `WORKSPACE_ROOT`. Any violation immediately returns a safe error string back to the LLM, teaching it to correct its pathing on the next loop iteration.

---

## ✨ Advanced Features Implementation

### REPL System Commands (State Interceptors)
To prevent "context trapping" where system commands are accidentally sent to the LLM, the `REPLAgent` implements input interceptors to manage state dynamically:
* `/sessions`: Bypasses the LLM to query `sessions.py` and print a formatted list of all saved chat histories.
* `/resume <id>`: Acts as a hot-swappable state mutator. It pauses the REPL loop, wipes the `self.messages` and `self.title` arrays, injects the requested JSON history, and re-renders the context without requiring a hard restart of the application.

### OpenCode-Inspired Tool Event Logger
To ensure full observability of the agent's autonomous actions, the base `Agent` class features a permanent audit logger. Triggered by the `_emit()` function, the system silently records a paper trail of every `tool_start`, `tool_end`, and `tool_error` directly to the hard drive, allowing the developer to review exactly what the AI accessed during its reasoning loops.

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites & Dependencies
Ensure Python 3 is installed. Install required libraries:
```bash
pip install openai python-dotenv requests markdownify trafilatura textual