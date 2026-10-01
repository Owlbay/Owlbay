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

DIRECTIONS = [
    ("Big Data", ["Cassandra", "Kafka", "Redis", "MySQL", "Data pipelines"]),
    ("Backend", ["Java", "Spring Boot", "Spring Cloud", "Go"]),
    ("AI Tooling", ["TypeScript", "Rust", "Coding agents", "LLM gateways"]),
    ("Apps", ["React", "Vue", "Kotlin", "Jetpack Compose"]),
]

QUERY = """query($login: String!) { user(login: $login) {
  repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
    nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
  }
} }"""
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

THEMES = {
    "dark": dict(bg="#0d1117", card="#0f1a14", border="#1f3326", text="#e6edf3",
                 muted="#8fa89a", faint="#3f5a49", accent="#4ade80", accent2="#a3e635",
                 chip="#132219", ramp=["#22c55e", "#4ade80", "#86efac", "#16a34a", "#a3e635", "#15803d", "#bbf7d0", "#3f5a49"]),
    "light": dict(bg="#ffffff", card="#f3faf5", border="#d5eadc", text="#0f172a",
                  muted="#5b6f63", faint="#b6cfbf", accent="#15803d", accent2="#4d7c0f",
                  chip="#e9f6ee", ramp=["#15803d", "#22c55e", "#86efac", "#166534", "#65a30d", "#4ade80", "#bbf7d0", "#cbd5d0"]),
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
    top = [(name, size) for name, size in sizes.most_common()
           if name != "Other" and size / total >= 0.005][:7]
    other = total - sum(size for _, size in top)
    languages = [(name, round(size / total * 100, 1)) for name, size in top]
    languages.append(("Other", round(other / total * 100, 1)))

    return {"languages": languages}


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
    w = 880
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
</defs>
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
    return body


def skills(t, data):
    w = 880
    parts = [f'<line x1="32" y1="0" x2="{w - 56}" y2="0" stroke="{t["border"]}"/>',
             f'<text x="32" y="44" font-family="{MONO}" font-size="11" letter-spacing="1" fill="{t["accent"]}">WHAT I WORK ON</text>']
    for i, (title, items) in enumerate(DIRECTIONS):
        x, y = 32 + (i % 2) * 420, 78 + (i // 2) * 62
        parts.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="15" font-weight="700" fill="{t["text"]}">{title}</text>')
        parts.append(f'<text x="{x}" y="{y + 22}" font-family="{FONT}" font-size="13" fill="{t["muted"]}">{escape(" · ".join(items))}</text>')

    parts.append(f'<line x1="32" y1="200" x2="{w - 56}" y2="200" stroke="{t["border"]}"/>')
    parts.append(f'<text x="32" y="228" font-family="{MONO}" font-size="11" letter-spacing="1" fill="{t["accent"]}">LANGUAGES</text>')
    parts.append(f'<text x="{w - 56}" y="228" text-anchor="end" font-family="{FONT}" font-size="11" fill="{t["muted"]}">by code size across my repositories</text>')
    x, bar_w = 32, w - 88
    parts.append(f'<clipPath id="bar"><rect x="32" y="242" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    colors = dict(zip((name for name, _ in data["languages"]), t["ramp"]))
    colors["Other"] = t["ramp"][-1]
    for name, pct in data["languages"]:
        seg = bar_w * pct / 100
        parts.append(f'<rect x="{x:.1f}" y="242" width="{seg + 0.5:.1f}" height="8" fill="{colors[name]}"/>')
        x += seg
    parts.append("</g>")
    x = 32
    for name, pct in data["languages"]:
        color = colors[name]
        text = f"{name} {pct:g}%"
        parts.append(f'<circle cx="{x + 4}" cy="273" r="4" fill="{color}"/>'
                     f'<text x="{x + 13}" y="277" font-family="{FONT}" font-size="12" fill="{t["muted"]}">{escape(text)}</text>')
        x += len(text) * 6.6 + 30
    return "\n".join(parts)


def profile(t, data):
    w, h = 880, 580
    label = ("yovinchen, Big Data Engineer building AI developer tools. Works on Big Data, Backend, "
             "AI Tooling and Apps. Languages: " + ", ".join(f"{n} {p}%" for n, p in data["languages"]))
    body = (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="{t["bg"]}" stroke="{t["border"]}"/>\n'
            f'{hero(t)}\n<g transform="translate(12 268)">{skills(t, data)}</g>')
    return svg(w, h, body, label)


def main():
    data = load_data()
    ASSETS.mkdir(exist_ok=True)
    for stale in ASSETS.glob("*.svg"):
        stale.unlink()
    for mode, t in THEMES.items():
        (ASSETS / f"profile-{mode}.svg").write_text(profile(t, data))


if __name__ == "__main__":
    main()
