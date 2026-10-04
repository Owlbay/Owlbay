"""Generate the profile SVG assets in light and dark variants.

Languages are measured by the code I wrote: every repository with my commits (own, org and upstream,
private included when PROFILE_TOKEN can read them) is cloned, and the lines added by my non-merge
commits on the default branch are counted by file extension. Only aggregates are written or logged.
"""
import base64
import datetime as dt
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
DATA_CACHE = ROOT / "data.json"
USERNAME = "Owlbay"
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
MY_EMAILS = {
    "gzh298255@gmail.com",
    "76760071+yovinchen@users.noreply.github.com",
    "76760071+owlbay@users.noreply.github.com",
    "2982554722@qq.com",
}
# Extension -> language; markup, styles and scripts count as Other, docs and data files are ignored
EXT_LANG = {
    "ts": "TypeScript", "tsx": "TypeScript", "mts": "TypeScript", "cts": "TypeScript",
    "js": "JavaScript", "jsx": "JavaScript", "mjs": "JavaScript", "cjs": "JavaScript",
    "java": "Java", "kt": "Kotlin", "kts": "Kotlin", "scala": "Scala", "groovy": "Groovy",
    "vue": "Vue", "svelte": "Svelte", "astro": "Astro",
    "go": "Go", "rs": "Rust", "py": "Python", "swift": "Swift", "m": "Objective-C",
    "c": "C", "h": "C", "cpp": "C++", "cc": "C++", "hpp": "C++", "cs": "C#", "php": "PHP", "rb": "Ruby", "dart": "Dart",
    "sql": "SQL", "lua": "Lua",
    "css": "Other", "scss": "Other", "less": "Other", "html": "Other", "htm": "Other",
    "sh": "Other", "bash": "Other", "zsh": "Other", "ps1": "Other", "bat": "Other",
}
SKIP_PATH = re.compile(
    r"(^|/)(node_modules|dist|build|out|target|vendor|\.next|\.nuxt|coverage|__snapshots__|generated|gen)/"
    r"|\.min\.(js|css)$|(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|Cargo\.lock|go\.sum)$"
    r"|\.(d\.ts|map)$"
)
LANG_COLORS = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Java": "#b07219", "Vue": "#41b883",
               "Go": "#00add8", "Rust": "#dea584", "Python": "#3572a5", "Kotlin": "#a97bff", "Other": "#8b97a8"}

DIRECTIONS = [
    ("Big Data", ["Cassandra", "Kafka", "Redis", "MySQL", "Data pipelines"]),
    ("Backend", ["Java", "Spring Boot", "Spring Cloud", "Go"]),
    ("AI Tooling", ["TypeScript", "Rust", "Coding agents", "LLM gateways"]),
    ("Apps", ["React", "Vue", "Kotlin", "Jetpack Compose"]),
]

QUERY = """query($login: String!) { user(login: $login) {
  createdAt
  followers { totalCount }
  pullRequests(states: MERGED) { totalCount }
  repositories(ownerAffiliations: OWNER, isFork: false, first: 100) { totalCount }
  contributionsCollection { totalCommitContributions contributionCalendar { totalContributions } }
} }"""
REPOS_QUERY = """query($from: DateTime!, $to: DateTime!) { viewer { contributionsCollection(from: $from, to: $to) {
  commitContributionsByRepository(maxRepositories: 100) { repository { nameWithOwner } }
} } }"""
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

THEMES = {
    "dark": dict(bg="#0d1117", card="#11161f", border="#222b38", text="#e6edf3",
                 muted="#8b97a8", faint="#4b5566", accent="#7dd3fc", accent2="#c4b5fd",
                 chip="#161d29"),
    "light": dict(bg="#ffffff", card="#f8fafc", border="#e2e8f0", text="#0f172a",
                  muted="#64748b", faint="#cbd5e1", accent="#0369a1", accent2="#6d28d9",
                  chip="#f1f5f9"),
}



def graphql(query, variables):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "owlbay-profile"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise RuntimeError(body["errors"][0].get("message", "GraphQL error"))
    return body["data"]


def accessible_repos():
    """Repositories the token can read (own, collaborator, org member), private included.
    Contribution queries hide private repositories from fine-grained tokens, so both lists are merged."""
    repos, page = set(), 1
    while True:
        request = urllib.request.Request(
            f"https://api.github.com/user/repos?affiliation=owner,collaborator,organization_member&per_page=100&page={page}",
            headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "owlbay-profile"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            batch = json.load(response)
        repos.update(r["full_name"] for r in batch if not r["fork"])
        if len(batch) < 100:
            return repos
        page += 1


def contributed_repos(since_year):
    repos = accessible_repos()
    for year in range(since_year, dt.date.today().year + 1):
        data = graphql(REPOS_QUERY, {"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
        for item in data["viewer"]["contributionsCollection"]["commitContributionsByRepository"]:
            repos.add(item["repository"]["nameWithOwner"])
    return sorted(repos)


def lang_of(path):
    if SKIP_PATH.search(path):
        return None
    base = path.rsplit("/", 1)[-1]
    return EXT_LANG.get(base.rsplit(".", 1)[-1].lower()) if "." in base else None


def scan_code(repos):
    """Lines added by my non-merge commits on each default branch. Repository names are never logged."""
    auth = base64.b64encode(f"x-access-token:{TOKEN}".encode()).decode()
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    sizes, commits, scanned = Counter(), 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, repo in enumerate(repos):
            target = os.path.join(tmp, str(i))
            cloned = subprocess.run(
                ["git", "-c", f"http.extraHeader=Authorization: Basic {auth}", "clone", "-q", "--bare",
                 "--single-branch", f"https://github.com/{repo}.git", target],
                capture_output=True, env=env,
            )
            if cloned.returncode:
                continue
            log = subprocess.run(
                ["git", "-C", target, "log", "HEAD", "--no-merges", "--no-renames", "--format=@@%ae", "--numstat"],
                capture_output=True, text=True, errors="replace",
            ).stdout
            mine, mine_here = False, 0
            for line in log.split("\n"):
                if line.startswith("@@"):
                    mine = line[2:].lower() in MY_EMAILS
                    mine_here += mine
                elif line and mine:
                    added, _deleted, path = line.split("\t", 2)
                    lang = lang_of(path) if added != "-" else None
                    if lang:
                        sizes[lang] += int(added)
            commits += mine_here
            scanned += mine_here > 0  # count only repositories that contain my commits
            subprocess.run(["rm", "-rf", target])
    return sizes, commits, scanned


def fetch_data():
    user = graphql(QUERY, {"login": USERNAME})["user"]
    repos = contributed_repos(int(user["createdAt"][:4]))
    sizes, commits, scanned = scan_code(repos)
    if not sizes:
        raise RuntimeError("no code scanned")
    print(f"checked {len(repos)} repositories; mine in {scanned}: {commits} commits, {sum(sizes.values())} lines")

    total = sum(sizes.values())
    top = [(name, size) for name, size in sizes.most_common()
           if name != "Other" and size / total >= 0.005][:7]
    other = total - sum(size for _, size in top)
    languages = [(name, round(size / total * 100, 1)) for name, size in top]
    languages.append(("Other", round(other / total * 100, 1)))

    calendar = user["contributionsCollection"]
    return {
        "generated": dt.date.today().isoformat(),
        "joined": user["createdAt"][:7],
        "contributions": calendar["contributionCalendar"]["totalContributions"],
        "commits": calendar["totalCommitContributions"],
        "merged_prs": user["pullRequests"]["totalCount"],
        "repositories": user["repositories"]["totalCount"],
        "followers": user["followers"]["totalCount"],
        "code": {"repos": scanned, "commits": commits, "lines": total},
        "languages": languages,
    }


def load_data():
    if TOKEN:
        try:
            data = fetch_data()
            DATA_CACHE.write_text(json.dumps(data, indent=2) + "\n")
            return data
        except Exception as exc:  # keep the last good numbers if the API fails
            print(f"using cached data: {exc}")
    return json.loads(DATA_CACHE.read_text())


def svg(width, height, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">\n{body}\n</svg>\n')


def chips(x, y, labels, t, size=11):
    out, cx = [], x
    for label in labels:
        w = len(label) * size * 0.62 + 18
        out.append(f'<rect x="{cx:.1f}" y="{y}" width="{w:.1f}" height="22" rx="11" fill="{t["chip"]}" stroke="{t["border"]}"/>'
                   f'<text x="{cx + w / 2:.1f}" y="{y + 15}" text-anchor="middle" font-family="{MONO}" font-size="{size}" fill="{t["muted"]}">{escape(label)}</text>')
        cx += w + 8
    return "".join(out)


def hero(t):
    w, h = 880, 280
    lines = [
        ("$", "whoami", t["text"]),
        ("", "big data engineer", t["muted"]),
        ("$", "cat now.txt", t["text"]),
        ("", "data pipelines, query tooling,", t["muted"]),
        ("", "and AI tools for developers", t["muted"]),
        ("$", "status", t["text"]),
    ]
    term = []
    y = 98
    for prompt, text, color in lines:
        if prompt:
            term.append(f'<text x="534" y="{y}" font-family="{MONO}" font-size="13" fill="{t["accent"]}">$</text>')
            term.append(f'<text x="550" y="{y}" font-family="{MONO}" font-size="13" fill="{color}">{escape(text)}</text>')
        else:
            term.append(f'<text x="550" y="{y}" font-family="{MONO}" font-size="13" fill="{color}">{escape(text)}</text>')
        y += 20
    term.append(f'<text x="550" y="{y}" font-family="{MONO}" font-size="13" fill="{t["muted"]}">mostly debugging</text>'
                f'<rect x="680" y="{y - 11}" width="8" height="14" fill="{t["accent"]}"><animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/></rect>')
    body = f'''<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["accent2"]}"/></linearGradient>
<pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{t["border"]}"/></pattern>
</defs>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{t["bg"]}" stroke="{t["border"]}"/>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16" fill="url(#dots)" opacity="0.6"/>
<text x="44" y="70" font-family="{MONO}" font-size="13" fill="{t["muted"]}">hi there, I'm</text>
<text x="42" y="122" font-family="{FONT}" font-size="50" font-weight="700" letter-spacing="-1.5" fill="{t["text"]}">Owlbay</text>
<rect x="44" y="140" width="64" height="3" rx="1.5" fill="url(#g)"/>
<text x="44" y="178" font-family="{FONT}" font-size="18" font-weight="600" fill="{t["text"]}">Big Data Engineer <tspan fill="url(#g)">→ AI Developer Tooling</tspan></text>
<text x="44" y="206" font-family="{FONT}" font-size="14" fill="{t["muted"]}">Building data platforms by day, agent tools by night.</text>
{chips(44, 228, ["Java", "Python", "Go", "Rust", "TypeScript"], t)}
<rect x="510" y="44" width="330" height="192" rx="12" fill="{t["card"]}" stroke="{t["border"]}"/>
<circle cx="530" cy="64" r="4.5" fill="#ff5f57"/><circle cx="545" cy="64" r="4.5" fill="#febc2e"/><circle cx="560" cy="64" r="4.5" fill="#28c840"/>
<text x="824" y="68" text-anchor="end" font-family="{MONO}" font-size="11" fill="{t["faint"]}">~/owlbay</text>
{"".join(term)}'''
    return svg(w, h, body, "Owlbay, Big Data Engineer building AI developer tools")








def languages_note(data):
    code = data.get("code")
    if not code:
        return "by code size across my repositories"
    return f"by lines I wrote: {code['commits']:,} commits across {code['repos']} repositories"


def skills(t, data):
    w, h = 880, 300
    parts = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["card"]}" stroke="{t["border"]}"/>',
             f'<text x="32" y="44" font-family="{MONO}" font-size="11" letter-spacing="1" fill="{t["accent"]}">WHAT I WORK ON</text>']
    for i, (title, items) in enumerate(DIRECTIONS):
        x, y = 32 + (i % 2) * 420, 78 + (i // 2) * 62
        parts.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="15" font-weight="700" fill="{t["text"]}">{title}</text>')
        parts.append(f'<text x="{x}" y="{y + 22}" font-family="{FONT}" font-size="13" fill="{t["muted"]}">{escape(" · ".join(items))}</text>')

    parts.append(f'<line x1="32" y1="200" x2="{w - 32}" y2="200" stroke="{t["border"]}"/>')
    parts.append(f'<text x="32" y="228" font-family="{MONO}" font-size="11" letter-spacing="1" fill="{t["accent"]}">LANGUAGES</text>')
    parts.append(f'<text x="{w - 32}" y="228" text-anchor="end" font-family="{FONT}" font-size="11" fill="{t["faint"]}">{escape(languages_note(data))}</text>')
    x, bar_w = 32, w - 64
    parts.append(f'<clipPath id="bar"><rect x="32" y="242" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    for name, pct in data["languages"]:
        seg = bar_w * pct / 100
        parts.append(f'<rect x="{x:.1f}" y="242" width="{seg + 0.5:.1f}" height="8" fill="{LANG_COLORS.get(name, LANG_COLORS["Other"])}"/>')
        x += seg
    parts.append("</g>")
    x = 32
    for name, pct in data["languages"]:
        color = LANG_COLORS.get(name, LANG_COLORS["Other"])
        text = f"{name} {pct:g}%"
        parts.append(f'<circle cx="{x + 4}" cy="273" r="4" fill="{color}"/>'
                     f'<text x="{x + 13}" y="277" font-family="{FONT}" font-size="12" fill="{t["muted"]}">{escape(text)}</text>')
        x += len(text) * 6.6 + 30
    label = "Big Data, Backend, AI Tooling, Apps. Languages: " + ", ".join(f"{n} {p}%" for n, p in data["languages"])
    return svg(w, h, "\n".join(parts), label)


def main():
    data = load_data()
    ASSETS.mkdir(exist_ok=True)
    for stale in [*ASSETS.glob("stats-*.svg"), *ASSETS.glob("stack-*.svg"), *ASSETS.glob("project-*.svg"), *ASSETS.glob("contrib-*.svg")]:
        stale.unlink()
    for mode, t in THEMES.items():
        (ASSETS / f"hero-{mode}.svg").write_text(hero(t))
        (ASSETS / f"skills-{mode}.svg").write_text(skills(t, data))


if __name__ == "__main__":
    main()
