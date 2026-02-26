"""
Skills manager — list, read, and create skill files (.md) from the skills directory.

Each skill is a .md file where:
- First line = short description (shown in skill listing)
- Rest = detailed content (loaded on demand by the agent)
"""

import os
from pathlib import Path


# Built-in tools that get added to the Anthropic API tools list
SKILLS_TOOLS = [
    {
        "name": "list_skills",
        "description": "List all available skills with their code names and short descriptions. Use this to discover what skills are available before loading them.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_skill",
        "description": "Read the full content of a skill by its code name. Load relevant skills before starting a task to get detailed instructions and knowledge.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill code name (filename without .md extension)",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "create_skill",
        "description": (
            "Create a new skill file with detailed knowledge and instructions. "
            "The content MUST be EXTREMELY detailed, comprehensive, and large. "
            "Include: step-by-step instructions, code examples, edge cases, "
            "best practices, common pitfalls, troubleshooting, and real-world scenarios."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill code name (will become the filename, use kebab-case)",
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Full skill content in markdown format. First line MUST be a short "
                        "one-line description. The rest should be extremely detailed and "
                        "comprehensive — the bigger and more thorough, the better."
                    ),
                },
            },
            "required": ["name", "content"],
        },
    },
]


class SkillsManager:
    """Manages skill files in the skills directory."""

    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> list[dict]:
        """
        Scan the skills directory and return a list of skills
        with their code names and short descriptions (first line).
        """
        skills = []
        if not self.skills_dir.exists():
            return skills

        for filepath in sorted(self.skills_dir.glob("*.md")):
            name = filepath.stem  
            description = ""
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    description = first_line.lstrip("#").strip()
            except Exception:
                description = "(unable to read)"
            skills.append({"name": name, "description": description})

        return skills

    def read_skill(self, name: str) -> str:
        """
        Read the full content of a skill by its code name.
        Returns the content string or an error message.
        """
        filepath = self.skills_dir / f"{name}.md"
        if not filepath.exists():
            available = [s["name"] for s in self.list_skills()]
            return f"Skill '{name}' not found. Available skills: {', '.join(available) or 'none'}"

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading skill '{name}': {e}"

    def create_skill(self, name: str, content: str) -> str:
        """
        Create a new skill .md file. Returns success message or error.
        """
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").strip("-_")
        if not safe_name:
            return f"Invalid skill name: '{name}'"

        filepath = self.skills_dir / f"{safe_name}.md"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            size = len(content)
            return f"Skill '{safe_name}' created successfully ({size:,} characters) at {filepath}"
        except Exception as e:
            return f"Error creating skill '{safe_name}': {e}"

    def get_skills_summary(self) -> str:
        """
        Get a formatted summary of available skills for the system prompt.
        """
        skills = self.list_skills()
        if not skills:
            return "No skills available yet. You can create new skills with create_skill tool."

        lines = []
        for s in skills:
            lines.append(f"- {s['name']}: {s['description']}")
        return "\n".join(lines)

    def execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """
        Execute a skills-related tool call. Returns the result as string.
        """
        if tool_name == "list_skills":
            skills = self.list_skills()
            if not skills:
                return "No skills found in the skills directory."
            lines = []
            for s in skills:
                lines.append(f"- {s['name']}: {s['description']}")
            return "\n".join(lines)

        elif tool_name == "read_skill":
            name = tool_args.get("name", "")
            return self.read_skill(name)

        elif tool_name == "create_skill":
            name = tool_args.get("name", "")
            content = tool_args.get("content", "")
            import telegram
            telegram.notify_skill_start(name)
            result = self.create_skill(name, content)
            safe_name = "".join(c for c in name if c.isalnum() or c in "-_").strip("-_") or name
            file_path = str(self.skills_dir / f"{safe_name}.md")
            telegram.notify_skill_done(name, len(content), content[:300], file_path)
            return result

        else:
            return f"Unknown skill tool: {tool_name}"

    @staticmethod
    def is_skill_tool(tool_name: str) -> bool:
        """Check if a tool name belongs to the skills system."""
        return tool_name in ("list_skills", "read_skill", "create_skill")
