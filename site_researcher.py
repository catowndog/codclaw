"""
Site Researcher — crawls reference/analog sites via MCP browser tools,
takes screenshots, analyzes structure, and creates detailed .md reports
that the agent uses as reference during development.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import display


RESEARCH_SYSTEM_PROMPT = """You are a web researcher analyzing a reference site.
Your goal is to thoroughly explore this website and create a VERY detailed report.

You have the rc-devtools MCP browser tools. Key tools (prefixed with rc-devtools__):

- `rc-devtools__navigate_page` — navigate to a URL
  params: `type` ("url"), `url`, `timeout` (ms), `enableDebugger` (bool), `ignoreCache` (bool)
- `rc-devtools__evaluate_script` — run JavaScript in the page
  param: `script` (NOT "expression")
- `rc-devtools__click` — click an element
  params: `uid` (element uid from snapshot), `dblClick` (bool)
- `rc-devtools__take_screenshot` — capture the current page
- `rc-devtools__get_snapshot` — get the current page DOM snapshot with element uids

IMPORTANT rc-devtools notes:
- `evaluate_script` uses param name `script`, NOT `expression`
- `click` uses `uid` (from snapshot), NOT CSS selectors
- For SPA sites, links from `a[href]` may not work — use `navigate_page` to each URL directly
- Screenshots return base64 — just call the tool, don't try to read the result
- Use `get_snapshot` to see page structure and get element `uid` values for clicking

## Research Process:

1. **Navigate to the main page** using `rc-devtools__navigate_page` with type="url"
2. **Take a screenshot** with `rc-devtools__take_screenshot`
3. **Get page snapshot** with `rc-devtools__get_snapshot` to see DOM structure
4. **Extract all navigation links** using `rc-devtools__evaluate_script`:
   script: `JSON.stringify([...document.querySelectorAll('a[href]')].map(a => ({href: a.href, text: a.textContent.trim()})).filter(a => a.text && a.href.startsWith('http')))`
5. **Visit each major section** (at least 5-10 pages):
   - Use `rc-devtools__navigate_page` with type="url" for each link (don't use click for navigation)
   - Take a screenshot of each page
   - Get snapshot to analyze structure
6. **Analyze the site structure**:
   - Extract page titles: `rc-devtools__evaluate_script` with script: `document.title`
   - Extract meta: script: `document.querySelector('meta[name=description]')?.content`
   - Note URL patterns (e.g. /blog/:slug, /dashboard/:section)
   - Identify tech stack: script: `JSON.stringify({react:!!window.__REACT_DEVTOOLS_GLOBAL_HOOK__,vue:!!window.__VUE__,next:!!window.__NEXT_DATA__,nuxt:!!window.__NUXT__})`
7. **Study UI/UX patterns**:
   - Navigation style (sidebar, topbar, hamburger)
   - Color scheme — extract with script: `getComputedStyle(document.body).backgroundColor`
   - Fonts — script: `getComputedStyle(document.body).fontFamily`
   - Form patterns, button styles, card layouts
8. **Extract CSS variables/theme**:
   script: `JSON.stringify([...document.styleSheets].flatMap(s => {try{return [...s.cssRules]}catch{return[]}}).filter(r => r.selectorText === ':root').flatMap(r => [...r.style].map(p => p + ': ' + r.style.getPropertyValue(p))))`
9. **Note special features**:
   - Auth flow (login/signup pages)
   - Search, filters, sorting, pagination
   - Modals, tooltips, notifications
   - Dark mode, language switcher

## Output Format:

After researching, use the write_file tool to save a detailed report to the specified path.
The report MUST be in markdown format with these sections:

```
# Site Analysis: {domain}

## Overview
- URL: ...
- Tech stack: ...
- Purpose: ...

## Site Map
- List of all discovered pages with URLs

## UI/UX Patterns
- Navigation, layout, components, colors, fonts
- CSS variables / theme values

## Page Details
### Homepage
- Structure, sections, CTA, layout
### [Other pages...]

## Key Features
- Notable functionality

## Design Patterns to Reuse
- Specific patterns worth copying for our project

## Screenshots
- List of screenshot paths taken
```

IMPORTANT:
- Be EXTREMELY detailed — this report will guide the development of a similar site
- Take screenshots of EVERY important page using rc-devtools__take_screenshot
- Use evaluate_script to extract real CSS values, colors, fonts, spacing
- Include specific colors (hex), font names, spacing values
- The more detail, the better the final product will be
"""


async def research_sites(agent, reference_sites: list[str], temp_dir: str):
    """
    Research each reference site before starting the main work loop.
    Creates .md reports in .temp/references/ for each site.
    Skips sites that already have a report (cache).

    Args:
        agent: AnthropicAgent instance (with MCP connected)
        reference_sites: List of URLs to research
        temp_dir: Path to .temp/ directory
    """
    if not reference_sites:
        return

    refs_dir = Path(temp_dir) / "references"
    screenshots_dir = refs_dir / "screenshots"
    refs_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    display.show_info(f"Research phase: {len(reference_sites)} reference site(s) to analyze")

    researched = []
    skipped = []

    for i, url in enumerate(reference_sites, 1):
        parsed = urlparse(url)
        domain = parsed.netloc.replace(":", "_").replace(".", "-")
        if not domain:
            display.show_warning(f"Invalid URL, skipping: {url}")
            continue

        report_path = refs_dir / f"{domain}.md"

        if report_path.exists():
            display.show_info(f"  [{i}/{len(reference_sites)}] {url} — cached, skipping")
            skipped.append(url)
            continue

        display.show_research_start(url, i, len(reference_sites))

        report_rel_path = f".temp/references/{domain}.md"
        screenshots_rel_path = f".temp/references/screenshots/{domain}"

        research_prompt = f"""Research this reference site thoroughly: {url}

Save your detailed report to: {report_rel_path}

Use rc-devtools MCP tools:
1. rc-devtools__navigate_page (type="url", url="{url}") to open the site
2. rc-devtools__take_screenshot to capture each page
3. rc-devtools__evaluate_script (script="...") to extract data from the page
4. rc-devtools__get_snapshot to see DOM structure
5. Navigate to at least 5-10 different pages using rc-devtools__navigate_page
6. Use write_file to save the final .md report to {report_rel_path}

Start NOW. Open {url} and begin the full site analysis.
Create the most detailed report possible — it will be used as a reference for building a similar site."""

        try:
            await agent.run_turn(research_prompt, RESEARCH_SYSTEM_PROMPT)
            researched.append(url)
            display.show_research_done(url)
        except Exception as e:
            display.show_error(f"Failed to research {url}: {e}")

    agent.reset_history()

    display.show_research_summary(
        total=len(reference_sites),
        researched=len(researched),
        cached=len(skipped),
    )


def get_reference_reports_summary(temp_dir: str) -> str:
    """
    Read all reference reports and return a summary for the system prompt.
    Lists all available reports with their paths.
    """
    refs_dir = Path(temp_dir) / "references"
    if not refs_dir.exists():
        return "No reference sites analyzed."

    reports = sorted(refs_dir.glob("*.md"))
    if not reports:
        return "No reference sites analyzed."

    lines = []
    for report in reports:
        domain = report.stem
        try:
            with open(report, "r", encoding="utf-8") as f:
                first_lines = []
                for _ in range(5):
                    line = f.readline().strip()
                    if line and not line.startswith("#"):
                        first_lines.append(line)
                summary = " | ".join(first_lines[:2]) if first_lines else "(report available)"
        except Exception:
            summary = "(report available)"

        lines.append(f"- **{domain}**: .temp/references/{domain}.md — {summary}")

    return "\n".join(lines)
