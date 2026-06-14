# Perplexity Research Terminal Online

An autonomous, terminal-based AI research assistant. This project demonstrates how to connect a Large Language Model to the physical internet and academic databases using custom Python tools, SDK tool-calling, and a multi-threaded Textual UI.

## 🎯 Objectives Achieved
* **Autonomous Tool Calling:** The AI intelligently decides when to use Google Search, when to scrape a specific URL, or when to dive into academic databases.
* **Live Web & Academic Integration:** * Integrated **Serper.dev** for real-time facts, weather, and current events.
  * Integrated **Trafilatura** for clean web text extraction with a strict 6,000-character budget.
  * Integrated **ArXiv API** (replicating AlphaXiv MCP tools) to autonomously discover and read scientific papers and preprints.
* **Parallel Execution:** Capable of executing multiple distinct tool requests simultaneously in a single turn.
* **Persistent Memory State:** Implemented a continuous `conversation_history` array that allows the AI to remember user context across the session.
* **Multi-Threaded UI:** Built a stateful Terminal User Interface (TUI) using `Textual`. Background worker threads ensure the UI never freezes.
* **Production Error Handling:** Added robust crash guards against `NoneType` data, 504 Gateway Timeouts, and empty API responses.
* **Live Token Tracking:** Intercepts LLM usage receipts to display real-time session token costs in the tool log.

## ⌨️ TUI Controls & Key Bindings
The standard TUI controls have been mapped to avoid standard typing conflicts:

* **`Ctrl + L`** : **Clear Screen** (Wipes the visual logs but keeps the AI's memory intact).
* **`Ctrl + K`** : **Wipe Memory** (Completely resets the conversation history array and zeroes out the token counter for a fresh start).
* **`Ctrl + Q`** : **Quit** (Safely terminates the application and background threads).

## 🚀 Built With
* Python
* Textual (TUI framework)
* OpenRouter API (LLM Routing)
* Serper API & ArXiv API