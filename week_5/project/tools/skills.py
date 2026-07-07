"""
tools/skills.py
===============
Manages the skills directory, including generating the catalog and loading specific skills.
"""

import os

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")

def get_skill_catalog() -> str:
    """Scans the skills subdirectories for SKILL.md files and returns metadata."""
    if not os.path.exists(SKILLS_DIR):
        return "No skills directory found."

    catalog_lines = []
    
    # Iterate through the FOLDERS in the skills directory
    for item in os.listdir(SKILLS_DIR):
        skill_dir_path = os.path.join(SKILLS_DIR, item)
        
        # Skip if it's not a directory
        if not os.path.isdir(skill_dir_path):
            continue
            
        skill_file_path = os.path.join(skill_dir_path, "SKILL.md")
        
        # Skip if there is no SKILL.md inside
        if not os.path.exists(skill_file_path):
            continue
            
        skill_name = item # The name of the folder is the skill name
        description = "No description provided."
        
        # Extract just the frontmatter description
        try:
            with open(skill_file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        yaml_text = parts[1].strip()
                        for line in yaml_text.split("\n"):
                            if line.lower().startswith("description:"):
                                description = line.split(":", 1)[1].strip()
                                break
        except Exception:
            pass

        catalog_lines.append(f"- **{skill_name}**: {description}")

    if not catalog_lines:
        return "No skills currently available."
        
    return "\n".join(catalog_lines)

def load_skill(skill_name: str) -> dict:
    """
    Reads the full SKILL.md content from a specific skill's folder.
    """
    # Now we look for the folder, and the SKILL.md inside it
    filepath = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    
    if not os.path.exists(filepath):
        return {"error": f"Skill '{skill_name}' not found. Make sure the folder exists and contains a SKILL.md file."}
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return {
                "skill_name": skill_name,
                "content": f.read()
            }
    except Exception as e:
        return {"error": f"Failed to read skill: {str(e)}"}
    
#   --- TOOL SCHEMA FOR THE SKILL MODULE ---

SKILL_TOOLS=[{
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "Load the full markdown instructions for a specific skill listed in your Skill Catalog. You MUST use this before attempting tasks related to these specialized frameworks or workflows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The exact name of the skill to load (e.g., 'git-conventional-commits')."
                    }
                },
                "required": ["skill_name"]
            }
        }
    }]