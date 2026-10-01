"""Generate the profile SVG assets in light and dark variants."""
import json
import os
import urllib.request
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
DATA_CACHE = ROOT / "data.json"
USERNAME = "yovinchen"
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
NON_CODE = {"CSS", "SCSS", "HTML", "PLpgSQL", "Shell", "Dockerfile", "Makefile"}
LANG_COLORS = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Java": "#b07219", "Vue": "#41b883",
               "Go": "#00add8", "Rust": "#dea584", "Python": "#3572a5", "Kotlin": "#a97bff", "Other": "#8b97a8"}

DIRECTIONS = [
    ("Big Data", ["Cassandra", "Kafka", "Redis", "MySQL", "Data pipelines"]),
    ("Backend", ["Java", "Spring Boot", "Spring Cloud", "Go"]),
    ("AI Tooling", ["TypeScript", "Rust", "Coding agents", "LLM gateways"]),
    ("Apps", ["React", "Vue", "Kotlin", "Jetpack Compose"]),
]

QUERY = """query($login: String!) { user(login: $login) {
  followers { totalCount }
  pullRequests(states: MERGED) { totalCount }
  repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
    totalCount
    nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
  }
  contributionsCollection { totalCommitContributions contributionCalendar { totalContributions } }
} }"""
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



def fetch_data():
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "yovinchen-profile"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        user = json.load(response)["data"]["user"]

    sizes = Counter()
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes["Other" if name in NON_CODE else name] += edge["size"]
    total = sum(sizes.values()) or 1
    top = [(name, size) for name, size in sizes.most_common() if name != "Other"][:7]
    other = total - sum(size for _, size in top)
    languages = [(name, round(size / total * 100, 1)) for name, size in top]
    languages.append(("Other", round(other / total * 100, 1)))

    calendar = user["contributionsCollection"]
    return {
        "contributions": calendar["contributionCalendar"]["totalContributions"],
        "commits": calendar["totalCommitContributions"],
        "merged_prs": user["pullRequests"]["totalCount"],
        "repositories": user["repositories"]["totalCount"],
        "followers": user["followers"]["totalCount"],
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
<text x="42" y="122" font-family="{FONT}" font-size="50" font-weight="700" letter-spacing="-1.5" fill="{t["text"]}">yovinchen</text>
<rect x="44" y="140" width="64" height="3" rx="1.5" fill="url(#g)"/>
<text x="44" y="178" font-family="{FONT}" font-size="18" font-weight="600" fill="{t["text"]}">Big Data Engineer <tspan fill="url(#g)">→ AI Developer Tooling</tspan></text>
<text x="44" y="206" font-family="{FONT}" font-size="14" fill="{t["muted"]}">Building data platforms by day, agent tools by night.</text>
{chips(44, 228, ["Java", "Python", "Go", "Rust", "TypeScript"], t)}
<rect x="510" y="44" width="330" height="192" rx="12" fill="{t["card"]}" stroke="{t["border"]}"/>
<circle cx="530" cy="64" r="4.5" fill="#ff5f57"/><circle cx="545" cy="64" r="4.5" fill="#febc2e"/><circle cx="560" cy="64" r="4.5" fill="#28c840"/>
<text x="824" y="68" text-anchor="end" font-family="{MONO}" font-size="11" fill="{t["faint"]}">~/yovinchen</text>
{"".join(term)}'''
    return svg(w, h, body, "yovinchen, Big Data Engineer building AI developer tools")






def stats(t, data):
    w, h = 880, 120
    items = [
        (f'{data["contributions"]:,}', "contributions this year"),
        (f'{data["commits"]:,}', "commits this year"),
        (f'{data["merged_prs"]:,}', "merged pull requests"),
        (f'{data["repositories"]:,}', "repositories"),
        (f'{data["followers"]:,}', "followers"),
    ]
    step = w / len(items)
    parts = [f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["card"]}" stroke="{t["border"]}"/>']
    for i, (value, label) in enumerate(items):
        x = 32 + i * step
        if i:
            parts.append(f'<line x1="{i * step}" y1="30" x2="{i * step}" y2="{h - 30}" stroke="{t["border"]}"/>')
        parts.append(f'<text x="{x}" y="66" font-family="{FONT}" font-size="32" font-weight="700" letter-spacing="-1" fill="{t["text"]}">{value}</text>'
                     f'<text x="{x}" y="90" font-family="{FONT}" font-size="12" fill="{t["muted"]}">{label}</text>')
    label = ", ".join(f"{v} {l}" for v, l in items)
    return svg(w, h, "\n".join(parts), label)


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
    parts.append(f'<text x="{w - 32}" y="228" text-anchor="end" font-family="{FONT}" font-size="11" fill="{t["faint"]}">by code size across my repositories</text>')
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
    for stale in [*ASSETS.glob("stack-*.svg"), *ASSETS.glob("project-*.svg"), *ASSETS.glob("contrib-*.svg")]:
        stale.unlink()
    for mode, t in THEMES.items():
        (ASSETS / f"hero-{mode}.svg").write_text(hero(t))
        (ASSETS / f"stats-{mode}.svg").write_text(stats(t, data))
        (ASSETS / f"skills-{mode}.svg").write_text(skills(t, data))


if __name__ == "__main__":
    main()
