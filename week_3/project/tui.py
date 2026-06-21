"""
TUIAgent — full-screen Textual UI inheriting from Agent.

Usage:
  python agent.py --tui

Tasks:
  1. class TUIAgent(Agent) — override _emit() for tool log panel
  2. class ResearchDeskApp(App) — layout, input, key bindings
  3. on_input_submitted -> worker -> self.chat() (inherited from Agent)
  4. Ctrl+L / Ctrl+K / Ctrl+Q from Week 2
"""
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, RichLog
from textual.binding import Binding
from textual import work

# Import the brain we just built
from agent import Agent

class TUIAgent(Agent):
    def __init__(self, session_id=None, ui_callback=None):
        super().__init__(session_id)
        self.ui_callback = ui_callback

    def _emit(self, event: str, **data) -> None:
        # 1. Send visual updates to the TUI sidebar (only if callback is attached)
        if hasattr(self, 'ui_callback') and self.ui_callback:
            if event == "tool_start":
                self.ui_callback(f"⚙️  [bold orange3]Starting:[/bold orange3] {data.get('name')}")
            elif event == "tool_end":
                self.ui_callback(f"✅ [bold green]Finished:[/bold green] {data.get('name')}")
            elif event == "tool_error":
                self.ui_callback(f"❌ [bold red]Error:[/bold red] {data.get('name')}")
                
        # 2. TRIGGER THE FILE LOGGER IN THE BASE CLASS!
        super()._emit(event, **data)

    def run(self):
        """Boot up the visual dashboard."""
        self.app = ResearchDeskApp(agent=self)
        self.app.run()


class ResearchDeskApp(App):
    """The actual layout and interface of the application."""
    
    # Simple CSS to create a split-screen view
    CSS = """
    #main-container { layout: horizontal; }
    #chat-panel { width: 3fr; border: solid green; }
    #tool-panel { width: 1fr; border: solid blue; padding: 1; }
    """

    # Keyboard shortcuts
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+l", "clear_chat", "Clear Chat"),
        Binding("ctrl+k", "clear_tools", "Clear Tool Log")
    ]

    def __init__(self, agent: TUIAgent):
        super().__init__()
        self.agent = agent

    def compose(self) -> ComposeResult:
        """Draw the screen."""
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            # Left Side: The Chat Window
            with Vertical(id="chat-panel"):
                self.chat_log = RichLog(highlight=True, markup=True, wrap=True)
                yield self.chat_log
                self.user_input = Input(placeholder="Ask your research desk...")
                yield self.user_input
            
            # Right Side: The AI's internal thoughts/tool logs
            with Vertical(id="tool-panel"):
                self.tool_log = RichLog(highlight=True, markup=True, wrap=True)
                yield self.tool_log
        yield Footer()

    def on_mount(self):
        """When the app starts, load the memory into the chat log."""
        # NEW: Show the human-readable title, but keep the ID in brackets just in case
        self.title = f"Research Desk — {self.agent.title} ({self.agent.session_id})"
        self.chat_log.write("[bold cyan]Welcome to your AI Research Desk![/bold cyan]")
        # ... (keep the rest of on_mount the same)
        
        # Print old memory so you can see past conversations!
        for msg in self.agent.messages:
            if msg['role'] == 'user':
                self.chat_log.write(f"\n[bold green]You:[/bold green] {msg['content']}")
            elif msg['role'] == 'assistant' and msg.get('content'):
                self.chat_log.write(f"\n[bold purple]Agent:[/bold purple] {msg['content']}")

    def log_tool(self, message: str):
        """Helper to write to the tool sidebar."""
        self.tool_log.write(message)

    @work(thread=True)
    def process_chat(self, user_text: str):
        """The background worker."""
        self.call_from_thread(self.chat_log.write, f"\n[bold green]You:[/bold green] {user_text}")
        self.call_from_thread(self.log_tool, "\n[dim]--- AI is thinking ---[/dim]")
        
        response = self.agent.chat(user_text)
        
        self.call_from_thread(self.chat_log.write, f"\n[bold purple]Agent:[/bold purple] {response}")
        self.title = f"Research Desk — {self.agent.title} ({self.agent.session_id})"
        
        # NEW: Close the loop in the tool panel so it never looks stuck!
        self.call_from_thread(self.log_tool, "[dim]--- Task Complete ---[/dim]\n")

    def on_input_submitted(self, event: Input.Submitted):
        """When you press Enter in the text box."""
        user_text = event.value.strip()
        if not user_text:
            return
        self.user_input.value = "" # Clear the text box
        self.process_chat(user_text) # Start thinking

    # Keyboard shortcut actions
    def action_clear_chat(self):
        self.chat_log.clear()
        
    def action_clear_tools(self):
        self.tool_log.clear()
        self.tool_log.write("[bold blue]Tool Execution Log[/bold blue]\n---")