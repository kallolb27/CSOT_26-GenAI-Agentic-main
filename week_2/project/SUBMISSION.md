# Week 2 Submission: Autonomous Research Agent

## 🛠️ Setup Instructions & Dependencies

### 1. Install Python Dependencies
Ensure you have Python 3.8+ installed. Run the following command to install all required libraries:
`pip install -r requirements.txt`

### 2. Configure Environment Variables
Duplicate the provided `.env.example` file, rename it to `.env`, and add your active API keys:
OPENROUTER_API_KEY=your_openrouter_api_key_here
SERPER_API_KEY=your_serper_dev_api_key_here

### 3. Run the Application
From the root of the project, launch the terminal agent:
`python week_2/project/agent.py`

*(Press `Ctrl+Q` at any time to safely quit the application).*

---

## 🧠 Project Write-Up

### 1. The Agent Loop
My autonomous loop runs in a background thread to keep the TUI responsive. It takes the user's prompt and sends it to the OpenRouter LLM along with an array of tool schemas. If the LLM requests a tool (like searching the web or scraping a URL), a Python `for` loop catches the `tool_calls` array, executes the requested functions locally, and appends the raw data back to the `conversation_history`. The loop repeats up to 6 times, allowing the AI to read a search snippet, decide to fetch the full URL, and synthesize a final response before returning control to the user.

### 2. Design Decision
I chose to implement a `session_tokens` counter and a strict context-truncation guard inside my web fetcher. Instead of blindly feeding a massive 30,000-word webpage into the LLM and draining my API budget, `trafilatura` cleanly extracts the article text, and Python explicitly chops it at 6,000 characters. This ensures the model stays fast, focused, and cost-effective while still getting the core information needed to answer the user's prompt.

### 3. Something That Surprised Me
I was surprised by how prone free models are to "hallucinating" tool usage. Initially, the AI would sometimes just generate text saying *"I have saved the file for you"* without actually triggering the JSON tool call array to execute the Python script. I learned that prompt engineering (giving the system prompt strict commands to *actually use* the tools) and adding crash-guards for empty `NoneType` API responses are mandatory for building a resilient agent.