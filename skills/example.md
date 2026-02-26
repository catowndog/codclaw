Example skill demonstrating the skills file format for the autonomous agent

# Example Skill

This is an example skill file that shows the correct format for creating skills.

## Skill File Format

Every skill is a `.md` (Markdown) file located in the `skills/` directory.

### Naming Convention
- File name = skill code name (kebab-case recommended)
- Examples: `web-scraping.md`, `data-analysis.md`, `api-testing.md`

### Content Structure
1. **First line** — short one-line description (shown in `list_skills` output)
2. **Rest** — detailed content with instructions, examples, and knowledge

## How the Agent Uses Skills

1. Agent calls `list_skills` to see available skills and their descriptions
2. Agent calls `read_skill` with a skill name to load its full content
3. Agent follows the instructions from the loaded skill
4. Agent can also create new skills with `create_skill` for reusable knowledge

## Example: Creating a Skill via CLI

```bash
python bot.py --create-skill "Detailed guide for working with PostgreSQL databases"
```

## Example: Agent Creating a Skill

The agent can call the `create_skill` tool during its work to save
reusable knowledge and patterns for future use.

## Tips for Good Skills

- Be as detailed as possible — the more detail, the better the agent performs
- Include code examples for every concept
- Cover edge cases and error handling
- Add troubleshooting sections
- Use clear headings and structure
