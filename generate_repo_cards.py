import json
import subprocess
import sys
from pathlib import Path

# The plugins we want to list
PLUGINS = [
    "improved-task",
    "improved-todowrite",
    "improved-webtools",
    "mcp-shim",
    "opencode-manager",
    "opencode-postgres-memory-plugin",
    "opencode-time-travel-plugin",
    "opencode-zotero-plugin",
    "prompt-router",
    "skill-reminder-injection",
]

def get_gh_stats(repo_name):
    try:
        # Get open issues count
        issues_out = subprocess.check_output(
            ["gh", "issue", "list", "--repo", f"dzackgarza/{repo_name}", "--state", "open", "--json", "number"],
            text=True
        )
        issues_count = len(json.loads(issues_out))

        # Get open PRs count
        prs_out = subprocess.check_output(
            ["gh", "pr", "list", "--repo", f"dzackgarza/{repo_name}", "--state", "open", "--json", "number"],
            text=True
        )
        prs_count = len(json.loads(prs_out))

        # Get description from package.json
        pkg_path = Path(repo_name) / "package.json"
        description = "No description available."
        if pkg_path.exists():
            with open(pkg_path, "r") as f:
                data = json.load(f)
                description = data.get("description", description)

        return {
            "name": repo_name,
            "description": description,
            "issues": issues_count,
            "prs": prs_count,
            "url": f"https://github.com/dzackgarza/{repo_name}"
        }
    except Exception as e:
        # Fallback if gh fails (e.g. not authenticated or repo missing)
        print(f"Error fetching stats for {repo_name}: {e}", file=sys.stderr)
        return {
            "name": repo_name,
            "description": "Stats unavailable.",
            "issues": "?",
            "prs": "?",
            "url": f"https://github.com/dzackgarza/{repo_name}"
        }

def generate_html(stats_list):
    cards_html = ""
    for s in stats_list:
        if not s: continue
        cards_html += f"""
        <div class="card" style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="margin-top: 0;"><a href="{s['url']}" style="color: #0366d6; text-decoration: none;">{s['name']}</a></h3>
            <p style="font-size: 0.9em; color: #555;">{s['description']}</p>
            <div class="stats" style="display: flex; gap: 10px; margin-top: 15px;">
                <a href="{s['url']}/issues" style="padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: #fff; text-decoration: none; background-color: #d73a49;">
                    <span>{s['issues']} Issues</span>
                </a>
                <a href="{s['url']}/pulls" style="padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: #fff; text-decoration: none; background-color: #28a745;">
                    <span>{s['prs']} PRs</span>
                </a>
            </div>
        </div>
        """
    return cards_html

if __name__ == "__main__":
    all_stats = [get_gh_stats(p) for p in PLUGINS]
    cards = generate_html(all_stats)
    
    section = f"""
    <section id="plugins" style="margin: 40px 0;">
        <h2 style="border-bottom: 2px solid #eee; padding-bottom: 10px;">Opencode Plugins</h2>
        <div class="repo-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; padding: 20px 0;">
            {cards}
        </div>
    </section>
    """
    
    print(section)
