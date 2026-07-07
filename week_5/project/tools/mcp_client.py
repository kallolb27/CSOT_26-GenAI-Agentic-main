import asyncio
import json
import os
import re
import httpx
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.client.stdio import stdio_client, StdioServerParameters # <-- NEW IMPORT

def load_mcp_config(path="config.json"):
    # ... (Keep your existing load_mcp_config function exactly the same) ...
    raw = open(path).read()

    def substitute(match):
        var = match.group(1)
        value = os.environ.get(var)
        if value is None:
            raise RuntimeError(f"config.json references ${{{var}}}, but it isn't set in your .env")
        return value

    resolved = re.sub(r"\$\{([A-Z0-9_]+)\}", substitute, raw)
    return json.loads(resolved)["mcpServers"]

class MCPManager:
    def __init__(self):
        self.stack = AsyncExitStack()
        self.openai_tools = []          
        self.tool_to_session = {}       

    async def connect_server(self, name: str, cfg: dict):
        """Connects to a single server and loads its tools dynamically."""
        conn_type = cfg.get("type", "sse") 
        
        # --- CONNECTION ROUTER ---
        if conn_type == "sse":
            http_client = await self.stack.enter_async_context(httpx.AsyncClient(headers=cfg.get("headers")))
            read, write, _ = await self.stack.enter_async_context(streamable_http_client(cfg["url"], http_client=http_client))
        elif conn_type == "stdio":
            server_params = StdioServerParameters(command=cfg["command"], args=cfg.get("args", []), env=cfg.get("env", None))
            read, write = await self.stack.enter_async_context(stdio_client(server_params))
        else:
            print(f"⚠️ Unknown connection type '{conn_type}' for server '{name}'.")
            return

        # --- INITIALIZE SESSION ---
        session = await self.stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        # --- FETCH TOOLS ---
        tools = await session.list_tools()
        for tool in tools.tools:
            namespaced_name = f"{name}_{tool.name}"
            self.tool_to_session[namespaced_name] = (session, tool.name)
            self.openai_tools.append({
                "type": "function",
                "function": {
                    "name": namespaced_name,
                    "description": f"[{name.upper()}] {tool.description}",
                    "parameters": tool.inputSchema,
                },
            })
        print(f"🔗 Connected MCP '{name}' ({conn_type}): {len(tools.tools)} tools loaded.")

    def disconnect_server(self, name: str):
        """Removes a server's tools from the active AI context."""
        # Remove from the routing dictionary
        keys_to_remove = [k for k in self.tool_to_session.keys() if k.startswith(f"{name}_")]
        for k in keys_to_remove:
            del self.tool_to_session[k]
        
        # Remove from the OpenAI schema list
        self.openai_tools = [t for t in self.openai_tools if not t["function"]["name"].startswith(f"{name}_")]
        print(f"🚫 Disconnected MCP '{name}'. Tools removed from AI context.")

    async def call_tool(self, namespaced_name: str, args: dict) -> str:
        """Executes a tool call on the remote MCP server using its true un-namespaced name."""
        session, original_name = self.tool_to_session[namespaced_name]
        result = await session.call_tool(original_name, args)
        return result.content[0].text if result.content else ""
    async def aclose(self):
        """Cleanly tears down all open connections."""
        await self.stack.aclose()