import os

# Import the catalog generator from your tools
from tools.skills import get_skill_catalog

def build_system_prompt(workspace_root: str, loaded_skills: list = None, mcp_servers: list = None) -> str:
    """
    Constructs the dynamic system prompt by loading the base AGENTS.md DNA
    and appending runtime context (Skills, MCP, Workspace).
    """
    prompt_parts = []

    # 1. THE DNA: Load your exact, highly detailed AGENTS.md file
    agent_file_path = os.path.join(os.path.dirname(__file__), "AGENTS.md")
    try:
        with open(agent_file_path, "r", encoding="utf-8") as f:
            prompt_parts.append(f.read())
    except FileNotFoundError:
        prompt_parts.append("You are Code Scout. (WARNING: AGENTS.md base file missing).")

    # 2. THE ENVIRONMENT: Where the agent is working
    prompt_parts.append("\n# CURRENT WORKSPACE CONTEXT")
    prompt_parts.append(f"You are currently operating in the following directory:\n{workspace_root}")

    # 3. THE APP STORE: Always inject the Skill Catalog (Discoverability)
    skill_catalog = get_skill_catalog()
    prompt_parts.append("\n# SKILL CATALOG")
    prompt_parts.append("You have access to the following specialized skills. If a task requires one of these skills, you MUST use the `load_skill` tool to read the full instructions before proceeding.")
    prompt_parts.append(skill_catalog)

    # 4. ACTIVE SKILLS: Inject the full bodies of anything explicitly requested
    if loaded_skills and len(loaded_skills) > 0:
        prompt_parts.append("\n# LOADED SKILLS")
        prompt_parts.append("You have explicitly loaded the following skill documents into memory:")
        for skill in loaded_skills:
            prompt_parts.append(f"\n--- SKILL: {skill['name']} ---")
            prompt_parts.append(skill['content'])
            prompt_parts.append("---------------------------")
    
    # 5. THE HANDS: External MCP Servers
    if mcp_servers and len(mcp_servers) > 0:
        prompt_parts.append("\n# ACTIVE MCP SERVERS")
        prompt_parts.append("You have access to the following external Model Context Protocol (MCP) servers:")
        for server in mcp_servers:
            prompt_parts.append(f"- {server}")

    # Stitch it all together
    return "\n".join(prompt_parts)