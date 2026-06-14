import os
import xml.etree.ElementTree as ET
import json
import requests
import trafilatura
from dotenv import load_dotenv
from openai import OpenAI
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Horizontal

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

# --- STABLE PRODUCTION TOOLS ---

def real_web_search(query: str, num_results: int = 4) -> str:
    """Search Google using Serper.dev and return live result snippets."""
    if not SERPER_API_KEY:
        return "Error: SERPER_API_KEY is not set in your .env file."
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        
        # Safety Guard: If API returned empty data or invalid JSON format
        if not data or not isinstance(data, dict):
            return "No live search results found (Invalid or empty API response)."
        
        results = []
        
        # Check if Google gave us a direct Answer Box
        if "answerBox" in data:
            answerBox = data.get("answerBox", {})
            if isinstance(answerBox, dict):
                answer = answerBox.get("answer") or answerBox.get("snippet")
                if answer:
                    results.append(f"DIRECT ANSWER BOX: {answer}\n---")
                
        for item in data.get("organic", []):
            if isinstance(item, dict):
                results.append(f"Title: {item.get('title')}\nURL: {item.get('link')}\nSnippet: {item.get('snippet')}\n---")
                
        return "\n".join(results) if results else "No live search results found."
    except Exception as e:
        return f"Error during live search execution: {str(e)}"

def real_web_fetch(url: str) -> str:
    """Fetch a real URL, scrape the main text body, and truncate cleanly."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        response.raise_for_status()
        
        text = trafilatura.extract(response.text, include_comments=False, include_tables=True)
        if not text:
            return "Error: Could not extract readable text body from this webpage."
            
        return text[:6000] + "\n\n[...Content truncated to save context budget...]" if len(text) > 6000 else text
    except Exception as e:
        return f"Error trying to fetch webpage: {str(e)}"
    
def discover_papers(query: str, max_results: int = 3) -> str:
    """Search for academic papers using the ArXiv API."""
    try:
        # Format the search query for the API
        search_query = query.replace(" ", "+")
        url = f"http://export.arxiv.org/api/query?search_query=all:{search_query}&start=0&max_results={max_results}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse the XML response from ArXiv
        root = ET.fromstring(response.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        results = []
        for entry in root.findall('atom:entry', ns):
            # Extract the specific ID, Title, and Abstract
            paper_id = entry.find('atom:id', ns).text.split('/abs/')[-1]
            title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
            summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
            
            results.append(f"Paper ID: {paper_id}\nTitle: {title}\nAbstract: {summary[:500]}...\n---")
            
        return "\n".join(results) if results else "No academic papers found for this query."
    except Exception as e:
        return f"Error discovering papers: {str(e)}"

def get_paper_content(paper_id: str) -> str:
    """Fetch the text content of a specific paper by its ArXiv ID."""
    # We can cleverly reuse our existing web scraper to read the paper's webpage!
    url = f"https://arxiv.org/html/{paper_id}v1"
    
    result = real_web_fetch(url)
    
    # If the HTML version doesn't exist, fallback to scraping the abstract page
    if "Error" in result or "not extract" in result:
        fallback_url = f"https://arxiv.org/abs/{paper_id}"
        return real_web_fetch(fallback_url)
        
    return result

# --- TOOL BLUEPRINTS ---

final_tools = [
    {
        "type": "function",
        "function": {
            "name": "real_web_search",
            "description": "Search Google for live, current information, real-time facts, or recent events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The specific target search query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "real_web_fetch",
            "description": "Fetch and read the full text content of a specific URL discovered from search results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The complete HTTP or HTTPS URL."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discover_papers",
            "description": "Search the AlphaXiv/ArXiv database for academic papers, preprints, and scientific research.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The scientific or academic search query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_paper_content",
            "description": "Read the content of a specific academic paper using its unique ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "The unique paper ID (e.g., '2401.12345')."}
                },
                "required": ["paper_id"],
            },
        },
    },
]

# --- THE INTERFACE LAYOUT ---

class PerplexityApp(App):
    CSS = """
    Horizontal {
        height: 1fr;
    }
    #chat-panel {
        width: 60%;
        border: solid $primary;
        background: $background;
    }
    #tool-panel {
        width: 40%;
        border: solid $warning;
        background: $background;
    }
    Input {
        dock: bottom;
        height: 3;
    }
    """
    
    # Updated Key Bindings to match rubric requirements
    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear Screen"),
        Binding("ctrl+k", "clear_history", "Wipe Memory"),
        Binding("ctrl+q", "quit", "Quit Application"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield RichLog(id="chat-panel", wrap=True, markup=True)
            yield RichLog(id="tool-panel", wrap=True, markup=True)
        yield Input(placeholder="Ask anything...")
        yield Footer()
        
    def on_mount(self) -> None:
        self.chat_log = self.query_one("#chat-panel", RichLog)
        self.tool_log = self.query_one("#tool-panel", RichLog)
        self.chat_log.write("[bold cyan]🔍 Perplexity Research Terminal Online.[/bold cyan]\n")
        self.tool_log.write("[bold yellow]🛠️ Live Tool Execution Stream Active.[/bold yellow]\n")
        
        self.conversation_history = [
            {
                "role": "system", 
                "content": "You are a professional research agent. IF the user asks for academic papers, scientific research, or specific studies, you MUST use the `discover_papers` and `get_paper_content` tools. For general facts or weather, use `real_web_search`. Summarize findings with clear markdown."
            }
        ]
        self.session_tokens = 0
        
    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return
            
        self.chat_log.write(f"[bold blue]You:[/bold blue] {user_text}")
        event.input.clear()
        
        self.conversation_history.append({"role": "user", "content": user_text})
        self.run_worker(self.run_perplexity_loop(), thread=True)

    async def run_perplexity_loop(self):
        """Executes the autonomous loop over the shared persistent history."""
        for iteration in range(6):
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=self.conversation_history,
                tools=final_tools,
            )
            
            # Safety Guard for API Network Failures / Timeouts
            if not response.choices:
                error_info = getattr(response, "error", "Unknown API Error. The model might be overloaded.")
                self.call_from_thread(self.chat_log.write, f"\n[bold red]Network Error:[/bold red] {error_info}\n")
                return
            
            message = response.choices[0].message
            self.conversation_history.append(message)
            
            # Token Usage Tracker
            if response.usage:
                turn_tokens = response.usage.total_tokens
                self.session_tokens += turn_tokens
                self.call_from_thread(
                    self.tool_log.write, 
                    f"[bold magenta]🪙 Token Usage ➔ This turn: {turn_tokens} | Session Total: {self.session_tokens}[/bold magenta]"
                )

            if not message.tool_calls:
                self.call_from_thread(self.chat_log.write, f"\n[bold green]Perplexity Engine:[/bold green] {message.content}\n")
                return
                
            for tool_call in message.tool_calls:
                tool_name = tool_call.id if not tool_call.function.name else tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                self.call_from_thread(self.tool_log.write, f"[bold yellow]⚡ RUNNING TOOL:[/bold yellow] {tool_name}({args})")
                if tool_name == "real_web_search":
                    tool_result = real_web_search(args.get("query"))
                elif tool_name == "real_web_fetch":
                    tool_result = real_web_fetch(args.get("url"))
                elif tool_name == "discover_papers":       # <-- ADD THIS
                    tool_result = discover_papers(args.get("query"))
                elif tool_name == "get_paper_content":     # <-- ADD THIS
                    tool_result = get_paper_content(args.get("paper_id"))
                else:
                    tool_result = "Error: Requested tool function not found."
                    
                # Safe preview execution check
                if tool_result is None:
                    tool_result = "Error: Tool execution returned nothing (None)."
                
                preview = tool_result[:200].replace('\n', ' ') + "..." if len(tool_result) > 200 else tool_result.replace('\n', ' ')
                self.call_from_thread(self.tool_log.write, f"[dim]➔ Tool returned: {preview}[/dim]\n")
                
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
        
    def action_clear_display(self) -> None:
        self.chat_log.clear()
        self.tool_log.clear()

    def action_clear_history(self) -> None:
        self.chat_log.clear()
        self.tool_log.clear()
        self.conversation_history = [
            {
                "role": "system", 
                "content": "You are a professional research agent. IF the user asks for academic papers, scientific research, or specific studies, you MUST use the `discover_papers` and `get_paper_content` tools. For general facts or weather, use `real_web_search`. Summarize findings with clear markdown."
            }
        ]
        self.session_tokens = 0
        self.chat_log.write("[bold cyan]🧹 Memory wiped clean and screen reset. Fresh conversation started![/bold cyan]\n")
if __name__ == "__main__":
    app = PerplexityApp()
    app.run()