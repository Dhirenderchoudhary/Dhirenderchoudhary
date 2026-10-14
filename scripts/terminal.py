"""Render the profile terminal: an animated zsh session with a portrait.

GitHub shows SVGs as images, so links inside one can't be clicked. The
terminal is drawn as one tall canvas and cut into horizontal slices; every
line with a link becomes its own slice, wrapped in <a> in README.md.

    pip install pillow pyfiglet
    python scripts/terminal.py
"""

import base64
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from urllib.parse import quote

import pyfiglet
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
PORTRAIT = ROOT / "profile" / "portrait.webp"
OUT_DIR = ROOT / "profile" / "terminal"
README = ROOT / "README.md"
VIEWS_TEMPLATE = ROOT / "views" / "template.js"

GH = "Dhirenderchoudhary"
USER, HOST = "dhirender", "fullstack"
SITE = "https://dhirenderchoudhary.com"
CALENDLY = "https://calendly.com/dhirenderchoudhary0001/meeting"


def merged(repo, terms=""):
    return f"https://github.com/{repo}/pulls?q=" + quote(f"is:pr author:{GH} is:merged {terms}".strip(), safe=":")


def pr(repo, n):
    return f"https://github.com/{repo}/pull/{n}"


FETCH = [
    ("OS", "Full-Stack Engineer"),
    ("Host", "SWE Intern @ Corsair (YC W25)"),
    ("Uptime", "21 years, Noida IN"),
    ("Kernel", "B.Tech ECE @ JIIT, class of '27"),
    ("Frontend", "React, Next.js, Tailwind"),
    ("Backend", "Node.js, Express, tRPC"),
    ("Data", "Postgres, MongoDB, MySQL, Redis"),
    ("Cloud", "AWS, CloudFront, Docker, Actions"),
    ("OSS", "116 PRs merged, 12 orgs"),
    ("Reviews", "180 PRs reviewed at Corsair"),
]

CORSAIR = [
    ("27 PRs merged across corsair + finch, 5 more open",
     "https://github.com/search?q=" + quote(f"is:pr author:{GH} org:corsairdev", safe=":") + "&type=pullrequests"),
    ("reviewed 180 PRs from 150+ contributors, 145 since merged",
     "https://github.com/corsairdev/corsair/pulls?q=" + quote(f"is:pr reviewed-by:{GH} -author:{GH}", safe=":")),
    ("9 plugins: WhatsApp, Workday, Salesforce, Databricks, Ollama,",
     merged("corsairdev/corsair", "plugin")),
    ("   Canvas LMS, Google Maps, Filevine, Reducto + an OCR web service",
     merged("corsairdev/corsair", "plugin")),
    ("PR checks, plugin validation gates, Jest across the monorepo",
     pr("corsairdev/corsair", 278)),
    ("fixed cyclic deps and formatting drift that broke CI",
     pr("corsairdev/corsair", 276)),
    ("OSS claim rules: 2 integrations per person, no unclaim once linked",
     pr("corsairdev/corsair", 826)),
    ("publicly recognized by the project creator", None),
]

OPEN_SOURCE = [
    ("Nano-Collective/nanocoder", 49, "terminal AI coding agent · 2.5k★"),
    ("corsairdev/corsair", 21, "agent integrations · 14k★"),
    ("learning-unlimited/ESP-Website", 19, "GSoC 2026 org"),
    ("RealDevSquad/website-backend", 6, "OOO request workflow, API"),
    ("OpenPrinting/cups-filters", 4, "foomatic-rip hardening"),
    ("lucid-softworks/browser", 4, "DOM spec fixes"),
    ("RealDevSquad/website-www", 3, "OOO request workflow, UI"),
    ("TeamShiksha/openlogo", 2, "logo API"),
    ("Nano-Collective/nanotune", 1, "fine-tuning toolkit"),
    ("Nano-Collective/prompt-scrubber", 1, "prompt redaction"),
    ("NVIDIA/aicr", 1, "GPU runtime on Kubernetes"),
    ("crbnos/carbon", 1, "manufacturing ERP · 2.7k★"),
    ("reticlehq/reticle", 1, "agent workspace · 1.2k★"),
    ("volcano-sh/website", 1, "CNCF Volcano"),
    ("The-OpenROAD-Project/OpenROAD", 1, "chip design · 3.1k★"),
    ("The-OpenROAD-Project/OpenROAD-flow-scripts", 1, "RTL-to-GDS flow"),
]

IN_REVIEW = "react · dicedb · hydradb · qa-agent · gitpick · braidpool"

HIGHLIGHTS = [
    ("nanocoder", "semantic memory, shipped in 5 phases", merged("Nano-Collective/nanocoder", "semantic memory")),
    ("nanocoder", "local web mode, shipped in 5 phases", merged("Nano-Collective/nanocoder", "web mode")),
    ("nanocoder", "#1067 optional OS sandbox for execute_bash", pr("Nano-Collective/nanocoder", 1067)),
    ("corsair", "#258 complete WhatsApp integration", pr("corsairdev/corsair", 258)),
    ("OpenROAD-flow", "#3961 PRE/POST Tcl hooks for every flow step", pr("The-OpenROAD-Project/OpenROAD-flow-scripts", 3961)),
    ("ESP-Website", "#4221 admin page for Stripe refunds", pr("learning-unlimited/ESP-Website", 4221)),
    ("cups-filters", "#744 reject unallowed FoomaticRIPPostPipe", pr("OpenPrinting/cups-filters", 744)),
    ("aicr", "#2138 UAT wiring from the reservation registry", pr("NVIDIA/aicr", 2138)),
]

PROJECTS = [
    ("jiitsphere", "replaces 4-5 JIIT portals, 500+ daily users", "https://www.jiitsphere.com/"),
    ("prd-army", "idea → PRD → tasks → PR audit, live GitHub sync", "https://prdarmy.dhirenderchoudhary.com/"),
    ("konoha-forma", "drag-and-drop form builder on the T3 stack", "https://konoha-forma.dhirenderchoudhary.com/"),
    ("zero-inbox", "Gmail, Calendar and AI agents in one inbox", "https://www.zeroinbox.fun"),
    ("unmarkk ★17", "strips metadata + AI provenance, fully local", f"https://github.com/{GH}/unmarkk"),
    ("kapat", "AI risk manager that catches fraud rings", f"https://github.com/{GH}/Kapat"),
]

LANGUAGES = [
    ("TypeScript", 78.6),
    ("JavaScript", 6.0),
    ("Python", 5.2),
    ("HTML", 5.1),
    ("CSS", 3.5),
]

CONTACTS = [
    ("web", "dhirenderchoudhary.com", SITE),
    ("github", GH, f"https://github.com/{GH}"),
    ("x", "@Dhirender_0001", "https://x.com/Dhirender_0001"),
    ("linkedin", "in/dhirender-choudhary0001", "https://www.linkedin.com/in/dhirender-choudhary0001/"),
    ("email", "dhirenderchoudhary0001@gmail.com", "mailto:dhirenderchoudhary0001@gmail.com"),
    ("calendly", "book a 30 min call", CALENDLY),
]

W = 980
X = 60
LINE = 30
ROW = 27
PALETTE = {
    "bg": "#0b0e14", "bar": "#131721", "edge": "#262b36",
    "prompt": "#ff9e64", "path": "#7aa2f7", "branch": "#bb9af7",
    "cmd": "#e6edf3", "muted": "#8b949e", "dim": "#5c6370",
    "key": "#7aa2f7", "text": "#c9d1d9", "ok": "#9ece6a", "accent": "#ff9e64",
}

PHOTO_W = 330
CELL_W, CELL_H, COLS = 4.6, 7.2, 72
GLYPHS = "dhirender"
PACE = 0.55
VIEWS_URL = "https://dhirender-views.vercel.app/api/views"


@dataclass
class Slice:
    top: int
    href: str | None
    src: str | None = None
    parts: list = field(default_factory=list)


class Session:
    def __init__(self):
        self.y = 78
        self.t = 0.04
        self.slices = [Slice(0, None)]
        self.fresh = False

    def place(self, top, href=None, src=None):
        top = int(top)
        if href or src:
            self.slices.append(Slice(top, href, src))
            self.fresh = True
        elif self.fresh:
            self.slices.append(Slice(top, None))
            self.fresh = False

    def add(self, svg):
        self.slices[-1].parts.append(svg)

    def fade(self, inner, delay=0.035, dur=0.3):
        self.t += delay * PACE
        self.add(f'<g class="fade" style="animation:fade {dur}s ease {self.t:.2f}s forwards">{inner}</g>')

    def line(self, spans, size=17, gap=LINE, href=None, src=None):
        self.place(self.y - size - (gap - size) // 2 + 2, href, src)
        self.fade(f'<text x="{X}" y="{self.y}" font-size="{size}">{spans}</text>')
        self.y += gap

    def prompt(self, cmd, gap_before=16):
        self.y += gap_before
        self.place(self.y - 21)
        self.t += 0.2 * PACE
        steps = max(len(cmd), 6)
        typing = (0.025 * steps + 0.2) * PACE
        spans = (
            f'{span("prompt", USER)}{span("dim", "@")}{span("path", HOST)}'
            f'{span("dim", " ~ ")}{span("branch", "git:(main)")}{span("prompt", " ❯")}{span("cmd", " " + cmd)}'
        )
        self.add(
            f'<g class="type" style="animation:type {typing:.2f}s steps({steps},start) {self.t:.2f}s forwards">'
            f'<text x="{X}" y="{self.y}" font-size="17">{spans}</text></g>'
        )
        self.t += typing
        self.y += LINE


def span(cls, text, x=None):
    pos = f' x="{x}"' if x is not None else ""
    return f'<tspan class="{cls}"{pos}>{escape(text)}</tspan>'


def lift(c):
    return round(255 * (c / 255) ** 0.85)


def photo_uri(src):
    buf = io.BytesIO()
    src.save(buf, "WEBP", quality=88, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def glyph_rows(src):
    rows = round(COLS * src.height / src.width * CELL_W / CELL_H)
    small = src.filter(ImageFilter.UnsharpMask(radius=8, percent=160, threshold=2)).resize((COLS, rows), Image.LANCZOS)
    alpha = small.getchannel("A")
    small = ImageEnhance.Contrast(ImageEnhance.Color(small.convert("RGB")).enhance(1.2)).enhance(1.3)
    small.putalpha(alpha)
    for r in range(rows):
        cells = []
        for c in range(COLS):
            red, green, blue, a = small.getpixel((c, r))
            if a < 110:
                continue
            cells.append((c, GLYPHS[(r * 3 + c) % len(GLYPHS)], f"#{lift(red):02x}{lift(green):02x}{lift(blue):02x}"))
        yield r, cells


def boot(s):
    for msg in ["Started dhirender.service", "Mounted /dev/jiit (B.Tech ECE '27)", "Joined corsair (YC W25) as SWE intern"]:
        s.line(span("dim", "[  ") + span("ok", "OK") + span("dim", "  ] ") + span("muted", msg), size=14, gap=18)
    s.line(
        span("dim", "[  ") + span("ok", "OK") + span("dim", "  ] ") + span("muted", "Served ")
        + span("accent", "__VIEWS__") + span("muted", " profile views"),
        size=14, gap=18, src=VIEWS_URL,
    )


def wordmark(s):
    art = [l for l in pyfiglet.figlet_format("DHIRENDER", font="ansi_shadow", width=200).splitlines() if l.strip()]
    left = (W - max(len(l) for l in art) * 6.62) / 2
    s.y += 22
    s.place(s.y - 16, SITE)
    for i, l in enumerate(art):
        s.fade(f'<text x="{left:.0f}" y="{s.y + i * 13}" xml:space="preserve" class="art" fill="url(#wm)">{escape(l)}</text>', delay=0.03)
    s.y += len(art) * 13 + 26
    s.fade(
        f'<text x="{W // 2}" y="{s.y}" text-anchor="middle" class="dim" font-size="14">'
        "dhirenderchoudhary.com · SWE intern @ Corsair (YC W25) · open source</text>"
    )
    s.y += 26


def fetch(s):
    s.prompt("fastfetch --logo ~/me.webp")
    src = Image.open(PORTRAIT).convert("RGBA")
    photo_h = PHOTO_W * src.height / src.width
    top = s.y - 14

    rows = list(glyph_rows(src))
    start = s.t
    glyphs = []
    for r, cells in rows:
        tspans = "".join(f'<tspan x="{X + c * CELL_W:.1f}" fill="{fill}">{escape(ch)}</tspan>' for c, ch, fill in cells)
        glyphs.append(
            f'<g class="fade" style="animation:fade .2s ease {start + (0.1 + r * 0.011) * PACE:.2f}s forwards">'
            f'<text class="px" y="{top + (r + 1) * CELL_H:.1f}">{tspans}</text></g>'
        )
    reveal = start + (0.1 + len(rows) * 0.011 + 0.35) * PACE
    s.add(
        f'<ellipse cx="{X + PHOTO_W / 2}" cy="{top + photo_h * 0.45:.0f}" rx="{PHOTO_W * 0.6:.0f}" ry="{photo_h * 0.45:.0f}" '
        f'fill="url(#glow)" class="fade" style="animation:fade 1s ease {reveal:.2f}s forwards"/>'
        f'<g class="ascii" style="animation:out .7s ease {reveal + 0.15:.2f}s forwards">{"".join(glyphs)}</g>'
        f'<image class="photo" style="animation:fade .9s ease {reveal:.2f}s forwards" x="{X}" y="{top}" '
        f'width="{PHOTO_W}" height="{photo_h:.0f}" href="{photo_uri(src)}"/>'
    )
    s.t = start + 0.3 * PACE

    ix = X + PHOTO_W + 36
    iy = top + 26
    gap = 34
    lines = [span("accent", USER) + span("dim", "@") + span("key", HOST), span("dim", "─" * 30)]
    lines += [span("key", key) + span("dim", ": ") + span("text", value) for key, value in FETCH]
    for i, l in enumerate(lines):
        s.fade(f'<text x="{ix}" y="{iy + i * gap}" font-size="18">{l}</text>', delay=0.04)
    swatch_y = iy + len(lines) * gap - 10
    colors = ["#f7768e", "#ff9e64", "#e0af68", "#9ece6a", "#7dcfff", "#7aa2f7", "#bb9af7", "#c0caf5"]
    s.fade("".join(f'<rect x="{ix + i * 26}" y="{swatch_y}" width="22" height="14" rx="2" fill="{c}"/>' for i, c in enumerate(colors)), delay=0.04)
    s.t = max(s.t, reveal + 0.6 * PACE)
    s.y = max(top + photo_h, swatch_y + 14) + 30


def corsair(s):
    s.prompt("cat ~/work/corsair.log")
    s.line(
        span("accent", "Jul 2026 → now") + span("text", "  Software Engineer Intern · ") + span("key", "Corsair (YC W25)")
        + span("muted", " · remote ↗"),
        href="https://github.com/corsairdev/corsair",
    )
    for text, href in CORSAIR:
        mark = span("dim", "    ") if text.startswith(" ") else span("ok", "  ✓ ")
        s.line(mark + span("text", text.strip()) + (span("dim", " ↗") if href else ""), size=16, gap=ROW, href=href)


def oss(s):
    s.prompt("gh pr list --author @me --state merged --oss | uniq -c")
    for repo, n, what in OPEN_SOURCE:
        s.line(span("ok", f"{n:>3}") + span("key", repo, x=X + 50) + span("muted", what, x=X + 520), size=16, gap=ROW, href=merged(repo))
    s.line(
        span("dim", "  =") + span("text", " 116 merged · 12 orgs · 16 repos", x=X + 50)
        + span("muted", "own and friends' repos excluded", x=X + 520),
        size=16, gap=ROW, href="https://github.com/search?q=" + quote(f"author:{GH} is:pr is:merged -user:{GH}", safe=":") + "&type=pullrequests",
    )
    s.line(
        span("branch", "  ~") + span("muted", f" in review: {IN_REVIEW}", x=X + 50),
        size=16, gap=ROW, href="https://github.com/search?q=" + quote(f"author:{GH} is:pr is:open -user:{GH}", safe=":") + "&type=pullrequests",
    )


def highlights(s):
    s.prompt("git log --oneline --grep=highlight")
    for where, what, href in HIGHLIGHTS:
        sha = hashlib.sha1((where + what).encode()).hexdigest()[:7]
        s.line(span("accent", sha) + span("branch", f"({where})", x=X + 84) + span("text", what, x=X + 250), size=16, gap=ROW, href=href)


def projects(s):
    s.prompt("ls -l ~/projects")
    for name, what, href in PROJECTS:
        s.line(span("dim", "drwxr-xr-x") + span("key", name, x=X + 116) + span("muted", what, x=X + 290), size=16, gap=ROW, href=href)


def languages(s):
    s.prompt("tokei ~ --sort code")
    track = 300
    for lang, pct in LANGUAGES:
        s.place(s.y - 21)
        fill = max(4, round(pct / 100 * track))
        bar = (
            f'<rect x="{X + 140}" y="{s.y - 11}" width="{track}" height="10" rx="5" fill="{PALETTE["edge"]}"/>'
            f'<rect x="{X + 140}" y="{s.y - 11}" width="{fill}" height="10" rx="5" fill="url(#wm)"/>'
        )
        s.fade(f'{bar}<text x="{X}" y="{s.y}" font-size="17">{span("key", lang)}{span("muted", f"{pct:.1f}%", x=X + 460)}</text>')
        s.y += 28


def contacts(s):
    s.prompt("cat ~/.contacts")
    for key, value, href in CONTACTS:
        s.line(span("key", key) + span("text", value, x=X + 140) + span("dim", " ↗"), href=href)


def outro(s):
    s.prompt("ssh hire@dhirender")
    s.line(span("ok", "connected") + span("text", " · I treat your product like my own. ") + span("accent", "book a call ↗"), href=CALENDLY)
    s.prompt("exit")
    s.line(span("dim", "Connection to ") + span("accent", "dhirender") + span("dim", " closed."))
    s.t += 0.2
    s.add(
        f'<g class="fade" style="animation:fade .2s ease {s.t:.2f}s forwards">'
        f'<rect class="cur" style="animation:blink 1.1s steps(1) {s.t + 0.1:.2f}s infinite" '
        f'x="{X}" y="{s.y - 14}" width="10" height="18" fill="{PALETTE["accent"]}"/></g>'
    )
    s.y += 22


def head(H):
    p = PALETTE
    classes = " ".join(f".{k}{{fill:{v}}}" for k, v in p.items() if k not in ("bg", "bar", "edge"))
    return f"""<defs>
<linearGradient id="wm" gradientUnits="userSpaceOnUse" x1="200" y1="0" x2="780" y2="0">
<stop offset="0" stop-color="#ff9e64"/><stop offset="0.5" stop-color="#f7768e"/><stop offset="1" stop-color="#bb9af7"/>
</linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#bb9af7" stop-opacity="0.28"/><stop offset="0.55" stop-color="#ff9e64" stop-opacity="0.08"/><stop offset="1" stop-color="#ff9e64" stop-opacity="0"/></radialGradient>
</defs>
<style>
text {{ font-size: 15px; white-space: pre; }}
.art {{ font-size: 11px; }}
.px {{ font-size: 8.5px; font-weight: 800; }}
.fade, .photo {{ opacity: 0; }}
.type {{ clip-path: inset(0 100% 0 0); }}
@keyframes type {{ to {{ clip-path: inset(0 0 0 0); }} }}
@keyframes fade {{ to {{ opacity: 1; }} }}
@keyframes out {{ to {{ opacity: 0; }} }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{
  .fade, .photo {{ opacity: 1 !important; animation: none !important; }}
  .ascii {{ display: none; }}
  .type {{ clip-path: inset(0 0 0 0) !important; animation: none !important; }}
  .cur {{ animation: none !important; }}
}}
{classes}
</style>
<rect x="20" y="16" width="{W - 40}" height="{H - 32}" rx="12" fill="{p["bg"]}" stroke="{p["edge"]}"/>
<path d="M20 28 A12 12 0 0 1 32 16 H{W - 32} A12 12 0 0 1 {W - 20} 28 V56 H20 Z" fill="{p["bar"]}"/>
<line x1="20" y1="56" x2="{W - 20}" y2="56" stroke="{p["edge"]}"/>
<circle cx="42" cy="36" r="6" fill="#ff5f57"/><circle cx="62" cy="36" r="6" fill="#febc2e"/><circle cx="82" cy="36" r="6" fill="#28c840"/>
<text x="{W // 2}" y="41" text-anchor="middle" class="dim" font-size="13">{USER}@{HOST} — zsh — 98×{round(H / 20)}</text>"""


def render():
    s = Session()
    for section in (boot, wordmark, fetch, corsair, oss, highlights, projects, languages, contacts, outro):
        section(s)
    H = round(s.y + 20)
    chrome = head(H)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.svg"):
        old.unlink()
    slices = [sl for sl in s.slices if sl.parts or sl.top == 0]
    bottoms = [sl.top for sl in slices[1:]] + [H]
    tags = []
    for i, (sl, bottom) in enumerate(zip(slices, bottoms)):
        h = bottom - sl.top
        name = f"{i:02d}.svg"
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {sl.top} {W} {h}" width="{W}" height="{h}" '
            "font-family=\"ui-monospace, 'SF Mono', SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, monospace\">\n"
            f"{chrome}\n" + "\n".join(sl.parts) + "\n</svg>\n"
        )
        if sl.src:
            VIEWS_TEMPLATE.write_text(f"export default {json.dumps(svg)};\n")
        else:
            (OUT_DIR / name).write_text(svg)
        img = f'<img align="left" width="{W}" src="{sl.src or "./profile/terminal/" + name}" alt="">'
        tags.append(f'<a href="{escape(sl.href)}">{img}</a>' if sl.href else img)

    block = "<!-- terminal:start -->\n" + "".join(tags) + "\n<!-- terminal:end -->"
    readme = README.read_text()
    README.write_text(re.sub(r"<!-- terminal:start -->.*?<!-- terminal:end -->", lambda _: block, readme, flags=re.S))
    size = sum(f.stat().st_size for f in OUT_DIR.glob("*.svg")) // 1024
    print(f"wrote {len(slices)} slices, {W}x{H}, {size} KB, {sum(1 for sl in slices if sl.href)} links, {s.t:.1f}s")


if __name__ == "__main__":
    render()
