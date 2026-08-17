#!/usr/bin/env python3
"""grimwild.py — Convert Grimwild module markdown to a styled PDF.

Usage: python3 grimwild.py <module.md> [-o <output.pdf>]

Pipeline: custom markdown -> HTML (semantic sections) -> headless Chromium -> PDF.
See AGENTS.md for the markdown syntax.
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

MD = MarkdownIt("commonmark")


def font_faces():
    """Generate @font-face rules for the local project fonts."""
    root = Path(__file__).parent / "fonts"
    faces = [
        ("Tiller", "fonnts.com-Tiller-Heavy.otf", 900, "normal"),
        ("Capito TRIAL 04", "CapitoTRIAL04-Light.otf", 300, "normal"),
        ("Capito TRIAL 04", "CapitoTRIAL04-LightItalic.otf", 300, "italic"),
        ("Capito TRIAL 04", "CapitoTRIAL04-Bold.otf", 700, "normal"),
        ("Capito TRIAL 04", "CapitoTRIAL04-BoldItalic.otf", 700, "italic"),
        ("Capito TRIAL 04", "CapitoTRIAL04-Heavy.otf", 800, "normal"),
    ]
    rules = []
    for family, rel, weight, style in faces:
        url = "file://" + str((root / rel).resolve())
        rules.append(
            f"@font-face {{ font-family: '{family}'; src: url('{url}') format('opentype'); "
            f"font-weight: {weight}; font-style: {style}; }}"
        )
    return "\n".join(rules)


# ---------------------------------------------------------------- parsing ---

DIV_OPEN = re.compile(r"^:::\s*\{([^}]*)\}\s*$")
DICE_POOL = re.compile(r"^(\dD)\s+(.*)$")
DICE_CHAL = re.compile(r"^(\dD)\s*\|\s*(.*)$")
LINK = re.compile(r"^(>>\*?)\s*(.*)$")


def parse_classes(attr):
    """'.pressure-pool repeat' -> ['pressure-pool', 'repeat']"""
    return [c.lstrip(".") for c in attr.split()]


def parse_pool(lines):
    pool = {"kind": "pool", "dice": None, "title": None, "items": [], "link": None}
    for s in lines:
        if not s:
            continue
        if s.startswith("## "):
            m = DICE_POOL.match(s[3:])
            if m:
                pool["dice"], pool["title"] = m.group(1), m.group(2)
        elif s.startswith("- "):
            pool["items"].append(s[2:])
        else:
            m = LINK.match(s)
            if m:
                pool["link"] = {
                    "from": pool["title"],
                    "to": m.group(2),
                    "type": "trigger" if "*" in m.group(1) else "lock",
                }
            else:
                print(
                    f"warning: unparsed line in pressure pool: {s!r}", file=sys.stderr
                )
    return pool


def parse_groups(lines):
    """A group is a lead paragraph followed by a '-' list."""
    groups, cur, buf = [], None, []

    def flush_buf():
        nonlocal cur, buf
        if buf:
            cur = {"lead": " ".join(buf), "items": []}
            groups.append(cur)
            buf = []

    for s in lines:
        if not s:
            flush_buf()
        elif s.startswith("- "):
            if cur is None:
                cur = {"lead": None, "items": []}
                groups.append(cur)
            cur["items"].append(s[2:])
        else:
            buf.append(s)
    flush_buf()
    return groups


def parse_challenges(lines):
    challenges = []
    for s in lines:
        if s.startswith("## "):
            m = DICE_CHAL.match(s[3:])
            if m:
                challenges.append(
                    {
                        "dice": m.group(1),
                        "title": m.group(2),
                        "traits": [],
                        "moves": [],
                        "fail": None,
                    }
                )
        elif s.startswith("* "):
            challenges[-1]["traits"].append(s[2:])
        elif s.startswith("- "):
            challenges[-1]["moves"].append(s[2:])
        elif s.startswith("x "):
            challenges[-1]["fail"] = s[2:]
    return challenges


def parse_div(attr, lines):
    classes = parse_classes(attr)
    if "module-icon" in classes:
        return {"kind": "icon", "svg": "\n".join(lines).strip()}
    if "pressure-pool" in classes:
        pool = parse_pool(lines)
        pool["props"] = [c for c in classes if c != "pressure-pool"]
        return pool
    if "useful-pieces" in classes:
        return {"kind": "pieces", "groups": parse_groups(lines)}
    if "set-it-up" in classes:
        return {"kind": "setup", "groups": parse_groups(lines)}
    if "challenges" in classes:
        return {"kind": "challenges", "challenges": parse_challenges(lines)}
    return {"kind": "div", "classes": classes}


def parse(text):
    lines = text.splitlines()
    mod = {"title": None, "blocks": []}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = DIV_OPEN.match(line)
        if m:
            inner = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                inner.append(lines[i].strip())
                i += 1
            i += 1  # closing :::
            block = parse_div(m.group(1), inner)
            if block["kind"] == "icon":
                mod["icon"] = block["svg"]
            else:
                mod["blocks"].append(block)
            continue
        if line.startswith("# "):
            mod["title"] = line[2:].strip()
            i += 1
            continue
        para = [line.strip()]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not DIV_OPEN.match(lines[i])
            and not lines[i].startswith("# ")
        ):
            para.append(lines[i].strip())
            i += 1
        mod["blocks"].append({"kind": "paragraph", "text": " ".join(para)})
    return mod


REPEAT_SVG = """<svg fill='var(--color-pool-icon)' version='1.1' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 94.073 94.072' xml:space='preserve'><g><path d='M91.465,5.491c-0.748-0.311-1.609-0.139-2.18,0.434l-8.316,8.316C72.046,5.057,60.125,0,47.399,0c-2.692,0-5.407,0.235-8.068,0.697C21.218,3.845,6.542,17.405,1.944,35.244c-0.155,0.599-0.023,1.235,0.355,1.724c0.379,0.489,0.962,0.775,1.581,0.775h12.738c0.839,0,1.59-0.524,1.878-1.313c3.729-10.193,12.992-17.971,23.598-19.814c1.747-0.303,3.525-0.456,5.288-0.456c8.428,0,16.299,3.374,22.168,9.5l-8.445,8.444c-0.571,0.572-0.742,1.432-0.434,2.179c0.311,0.748,1.039,1.235,1.848,1.235h28.181c1.104,0,2-0.896,2-2V7.338C92.7,6.53,92.211,5.801,91.465,5.491z'/><path d='M90.192,56.328H77.455c-0.839,0-1.59,0.523-1.878,1.312c-3.729,10.193-12.992,17.972-23.598,19.814c-1.748,0.303-3.525,0.456-5.288,0.456c-8.428,0-16.3-3.374-22.168-9.5l8.444-8.444c0.572-0.572,0.743-1.432,0.434-2.179c-0.31-0.748-1.039-1.235-1.848-1.235H3.374c-1.104,0-2,0.896-2,2v28.181c0,0.809,0.487,1.538,1.235,1.848c0.746,0.31,1.607,0.138,2.179-0.435l8.316-8.315c8.922,9.183,20.843,14.241,33.569,14.241c2.693,0,5.408-0.235,8.069-0.697c18.112-3.146,32.789-16.708,37.387-34.547c0.155-0.6,0.023-1.234-0.354-1.725C91.395,56.615,90.811,56.328,90.192,56.328z'/></g></svg>"""

END_SVG = """<svg viewBox="0 0 16 16" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" class="si-glyph si-glyph-circle-star" fill="var(--color-pool-icon)"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <title>1047</title> <defs> </defs> <g stroke="none" stroke-width="1" fill="none" fill-rule="evenodd"> <path d="M8,0.062 C3.581,0.062 0,3.621 0,8.009 C0,12.399 3.581,15.958 8,15.958 C12.418,15.958 16,12.398 16,8.009 C16,3.621 12.418,0.062 8,0.062 L8,0.062 Z M11.108,12.025 L8.021,9.902 L4.933,12.025 L6.112,8.59 L3.024,6.465 L6.841,6.465 L8.021,3.03 L9.201,6.465 L13.017,6.465 L9.93,8.59 L11.108,12.025 L11.108,12.025 Z" fill="var(--color-pool-icon)" class="si-glyph-fill"> </path> </g> </g></svg>
"""

LOCK_SVG = "<svg viewBox='0 0 10 10'><rect x='2' y='4.4' width='6' height='4.4' rx='1' fill='var(--color-pool-icon)'/><path d='M3.2 4.4 V3.1 a1.8 1.8 0 0 1 3.6 0 V4.4' fill='none' stroke='var(--color-pool-icon)' stroke-width='1.2'/></svg>"

TRIGGER_SVG = "<svg viewBox='0 0 10 10'><circle cx='5' cy='5' r='3.9' fill='none' stroke='var(--color-pool-icon)' stroke-width='1'/><path d='M3.9 2.9 L6.1 5 L3.9 7.1' fill='none' stroke='var(--color-pool-icon)' stroke-width='1' stroke-linecap='round'/></svg>"

# Module icon: stylised goblin mask matching the golden example.
DEFAULT_ICON_SVG="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" ><path d="M0 0h512v512H0z" fill="#000" fill-opacity="1"></path><g><path d="M62.5 17.28c-9.747.288-20.824 5.23-29.844 14.25-15.192 15.193-18.838 36.194-8.125 46.907 7.99 7.988 21.716 8.027 34.47 1.22 16.167 30.05 42.154 57.687 71.438 76.374-18.77 24.156-29.97 54.48-29.97 87.376h18.688c0-28.9 9.828-55.474 26.344-76.53l2.156 39.405C274.5 320.554 402.09 428.196 496.062 494.94c-65.54-95.294-176.99-224.638-288.687-348.407l-38.97-2.124c20.764-15.68 46.638-24.967 74.72-24.97V100.75c-32.2.002-61.945 10.725-85.844 28.78-18.696-29.383-46.39-55.48-76.53-71.686 6.795-12.748 6.796-26.423-1.188-34.407-4.352-4.352-10.393-6.352-17.062-6.156z" fill="#fff" fill-opacity="1"></path></g></svg>"""

# ------------------------------------------------------------------ icons ---

# Item markers are Unicode glyphs rendered with DejaVu Sans (the font that
# covers them all, so they share metrics and print at a uniform size).
MARKER_CHARS = {
    "dot": "\u25c9",  # ◉ fisheye (pools, moves)
    "triangle": "\u25b8",  # ▸ (useful pieces)
    "box": "\u25a2",  # ▢ (set it up)
    "star": "\u2731",  # ✱ (traits)
    "cross": "\u2718",  # ✘ (fail state)
}


# --------------------------------------------------------------- rendering ---


def inline(text):
    return MD.renderInline(text.strip())


def render_pool(pool):
    classes = " ".join(["pool"] + pool["props"])
    prop_icon = ""
    if "repeat" in pool["props"]:
        prop_icon = f"<span class='prop'>{REPEAT_SVG}</span>"
    elif "end" in pool["props"]:
        prop_icon = f"<span class='prop'>{END_SVG}</span>"
    items = "".join(f"<li>{inline(i)}</li>" for i in pool["items"])
    html = (
        f"<div class='{classes}'>"
        f"<header><span class='dice'>{pool['dice']}</span>"
        f"<h2>{inline(pool['title'])}</h2>{prop_icon}</header>"
        f"<ul class='m-dot'>{items}</ul></div>"
    )
    if pool["link"]:
        link_icon = LOCK_SVG if pool["link"]["type"] == "lock" else TRIGGER_SVG
        html += (
            f"<div class='pool-link {pool['link']['type']}'>"
            f"{link_icon}</div>"
        )
    return html


def render_pools(pools):
    body = "".join(render_pool(p) for p in pools)
    return f"<section class='pools'>{body}</section>"


def render_banded(kind, title, groups, marker):
    out = []
    for g in groups:
        lead = f"<p class='lead'>{inline(g['lead'])}</p>" if g["lead"] else ""
        cls = "two-col" if len(g["items"]) > 6 else ""
        items = "".join(f"<li>{inline(i)}</li>" for i in g["items"])
        out.append(
            f"<div class='group'>{lead}<ul class='{marker} {cls}'>{items}</ul></div>"
        )
    return (
        f"<section class='banded {kind}'><h2 class='banner'>{title}</h2>"
        f"<div class='cols'>{''.join(out)}</div></section>"
    )


def render_challenges(challenges):
    out = []
    for c in challenges:
        traits = "".join(f"<li>{inline(t)}</li>" for t in c["traits"])
        moves = "".join(f"<li>{inline(m)}</li>" for m in c["moves"])
        fail = ""
        if c["fail"]:
            fail = f"<p class='fail'>{c["fail"]}</p>"
        out.append(
            f"<div class='challenge'>"
            f"<header><span class='dice'>{c['dice']}</span>"
            f"<span class='sep'>|</span><h2>{inline(c['title'])}</h2></header>"
            f"<ul class='m-star traits'>{traits}</ul>"
            f"<ul class='m-dot moves'>{moves}</ul>{fail}</div>"
        )
    return f"<section class='challenges'>{''.join(out)}</section>"


def render(mod, css=None):
    if css is None:
        css = BASE_CSS + "\n" + font_faces()
    css = build_css(css)
    head_parts, body_parts, pool_run = [], [], []

    def flush_pools():
        nonlocal pool_run
        if pool_run:
            body_parts.append(render_pools(pool_run))
            pool_run = []

    seen_section = False
    for b in mod["blocks"]:
        if b["kind"] == "pool":
            seen_section = True
            pool_run.append(b)
            continue
        flush_pools()
        if b["kind"] == "paragraph":
            text = b["text"]
            if not seen_section:
                if text.startswith("*") and text.endswith("*"):
                    head_parts.append(f"<p class='hook'>{inline(text)}</p>")
                else:
                    head_parts.append(f"<p class='intro'>{inline(text)}</p>")
            elif re.match(r"^\*\*Mix It Up\*\*", text):
                body_parts.append(f"<p class='mix-it-up'>{inline(text)}</p>")
            else:
                body_parts.append(f"<p>{inline(text)}</p>")
        elif b["kind"] == "pieces":
            seen_section = True
            body_parts.append(
                render_banded(
                    "useful-pieces", "Useful Pieces", b["groups"], "m-triangle"
                )
            )
        elif b["kind"] == "setup":
            seen_section = True
            body_parts.append(
                render_banded("set-it-up", "Set It Up", b["groups"], "m-box")
            )
        elif b["kind"] == "challenges":
            seen_section = True
            body_parts.append(render_challenges(b["challenges"]))
    flush_pools()

    hooks = "".join(h for h in head_parts if "class='hook'" in h)
    intros = "".join(h for h in head_parts if "class='intro'" in h)
    return TEMPLATE.format(
        title=inline(mod["title"] or ""),
        goblin_icon=mod.get("icon") or DEFAULT_ICON_SVG,
        hooks=f"<div class='hooks'>{hooks}</div>" if hooks else "",
        intros=intros,
        body="\n".join(body_parts),
        css=css,
    )


# -------------------------------------------------------------------- CSS ---


def build_css(css):
    sizes = {
        "dot": "0.95em",
        "triangle": "0.95em",
        "box": "0.95em",
        "star": "0.82em",
        "cross": "1.2em",
    }
    markers_css = ""
    for sel, key in [
        ("ul.m-dot li", "dot"),
        ("ul.m-triangle li", "triangle"),
        ("ul.m-box li", "box"),
        ("ul.m-star li", "star"),
        (".challenge .fail", "cross"),
    ]:
        markers_css += f"""
{sel}::before {{ content: "{MARKER_CHARS[key]}"; font-size: {sizes[key]}; }}"""
    return css.replace("/*MARKERS*/", markers_css)


BASE_CSS = """
:root {
  --color-title: #16130d;
  --color-text: #211d15;
  --color-heading: #221e15;
  --color-banner-text: #231f16;
  --color-muted: #6d675a;
  --color-pool-icon: #8e877f;
  --color-dice-bg: #9d927f;
  --color-banner: #b3a897;
  --color-page-far: #cfc3aa;
  --color-page-mid2: #ddd3bd;
  --color-pool-header: #ddd7ca;
  --color-page-mid1: #e9e2cf;
  --color-pool-link-bg: #e9e3d2;
  --color-page-start: #efe9d8;
  --color-cream: #f4eee0;
  --color-cream2: #f6f1e4;
  --color-transparent: rgba(0,0,0,0);
  --color-head-bg: rgba(246,241,230,0.55);
  --color-card-bg: rgba(247,242,231,0.72);
  --color-cols-bg: rgba(247,242,231,0.78);
  --color-card-solid: rgba(247,242,231,1);
  --color-shadow-dark: rgba(30,25,15,0.35);
  --color-border-module: rgba(52,45,33,0.65);
  --color-border-hook: rgba(60,50,35,0.18);
  --color-border-title: rgba(60,50,35,0.22);
  --color-border-challenge-light: rgba(80,70,52,0.15);
  --color-border-challenge: rgba(80,70,52,0.22);
  --color-border-card: rgba(80,70,52,0.25);
  --color-border-header: rgba(80,70,52,0.30);
  --color-border-section: rgba(80,70,52,0.45);
  --color-vignette: rgba(84,70,48,0.27);
}

@page { size: 176mm 250mm; margin: 0; }
* { box-sizing: border-box; print-color-adjust: exact; -webkit-print-color-adjust: exact; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Capito TRIAL 04", "Noto Serif", serif;
  font-weight: 300;
  font-size: 8.6pt; line-height: 1.24; color: var(--color-text);
  background:
    radial-gradient(115% 85% at 50% 42%, var(--color-transparent) 52%, var(--color-vignette) 100%),
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.42 0 0 0 0 0.38 0 0 0 0 0.30 0 0 0 0.05 0'/></filter><rect width='240' height='240' filter='url(%23n)'/></svg>"),
    linear-gradient(165deg, var(--color-page-start) 0%, var(--color-page-mid1) 38%, var(--color-page-mid2) 72%, var(--color-page-far) 100%);
  width: 176mm; height: 250mm; overflow: hidden;
}
.page { padding: 8mm 10.5mm 7mm; height: 100%; }

/* ---- module header ---- */
.module-head {
  position: relative; border: 0.45mm solid var(--color-border-module);
  border-radius: 1mm; padding: 2.2mm 4mm 2.6mm; margin-top: 4.5mm;
  background: var(--color-head-bg);
}
.module-art {
  position: absolute; top: -4.6mm; left: 4mm; width: 15mm; height: 15mm;
  background: var(--color-head-bg);
  border-radius: 0.8mm; box-shadow: 0.4mm 0.4mm 0.8mm var(--color-shadow-dark);
}
.module-art svg { display: block; width: 100%; height: 100%; }
h1 {
  font-family: "Tiller", "Noto Sans", sans-serif; font-weight: 900; text-transform: uppercase;
  text-align: center; font-size: 22pt; letter-spacing: 0.01em;
  margin: 0.2mm 0 2mm; padding-bottom: 1mm; color: var(--color-title);
  border-bottom: 0.25mm solid var(--color-border-challenge);
}
.hooks { display: flex; margin: 0 2mm 1.8mm; }
.hook {
  flex: 1; margin: 0; padding: 0 3mm; font-style: italic; font-size: 8pt;
  color: var(--color-muted); text-align: center;
}
.hook + .hook { border-left: 0.25mm solid var(--color-border-hook); }
.intro { margin: 1.8mm 0 0; text-align: justify; font-size: 8.6pt; }
.intro strong { font-variant: small-caps; letter-spacing: 0.02em; }

/* ---- generic lists with Unicode markers ---- */
strong { font-weight: 700; }
ul { margin: 0; padding: 0; list-style: none; }
li { position: relative; padding-left: 3.4mm; margin: 0.35mm 0; }
li::before {
  position: absolute; left: 0.2mm; top: 0.08em;
  font-family: "DejaVu Sans", sans-serif; font-size: 0.95em; line-height: 1;
}
/*MARKERS*/

/* ---- pressure pools ---- */
.pools {
  display: flex; align-items: stretch;
  gap: 6.5mm; margin: 4.5mm 0 0;
}
.pool {
  flex: 1; background: var(--color-card-bg); border-radius: 0.7mm;
  box-shadow: 0 0 0 0.25mm var(--color-border-card);
}
.pool header {
  display: flex; align-items: center; gap: 1.7mm;
  background: var(--color-pool-header);
  border-radius: 0.65mm; padding: 1mm 1.5mm;
  box-shadow: 0 0 0 0.25mm var(--color-border-header);
}
.pool .dice {
  font-family: "Noto Sans", sans-serif; font-weight: 800; font-size: 7.6pt;
  background: var(--color-dice-bg); color: var(--color-heading); border-radius: 0.45mm;
  padding: 0.15mm 1.1mm; letter-spacing: 0.02em;
}
.pool h2 {
  margin: 0; font-size: 10pt; font-variant: small-caps; font-weight: 800;
  color: var(--color-heading); white-space: nowrap;
}
.pool .prop { margin-left: auto; width: 2.8mm; height: 2.8mm; }
.pool .prop svg { width: 100%; height: 100%; display: block; }
.pool ul { padding: 1.1mm 1.5mm 1.3mm; }
.pool-link {
  position: relative; flex: none; align-self: flex-start;
  width: 6.5mm; height: 6mm; margin: 0 -6.5mm;  /* exactly bridges the flex gap */
}
.pool-link::before {  /* line at header middle, spanning the gap only */
  content: ""; position: absolute; left: 0; right: 0; top: 2.6mm;
  border-top: 0.35mm solid var(--color-pool-icon);
}
.pool-link svg {  /* centered on the line, backing hides the line crossing */
  position: relative; display: block; width: 3.5mm; height: 3.5mm;
  margin: 0.85mm auto 0; background: var(--color-pool-link-bg); border-radius: 50%;
}

/* ---- banded sections (Useful Pieces / Set It Up) ---- */
.banded {
  margin-top: 4.5mm; border-radius: 0.8mm; overflow: hidden;
  box-shadow: 0 0 0 0.3mm var(--color-border-section);
}
.banner {
  margin: 0; text-align: center; font-size: 9.5pt; text-transform: uppercase;
  font-weight: 800; color: var(--color-banner-text);
  background: var(--color-banner);
  padding: 0.9mm 0 1.1mm;
}
.cols { display: flex; background: var(--color-cols-bg); }
.group { flex: 1; padding: 1.5mm 2mm 1.7mm; }
.group + .group { border-left: 0.25mm solid var(--color-border-title); }
.lead { margin: 0 0 0.8mm; text-align: left; }
.lead strong { font-variant: small-caps; font-weight: 800; letter-spacing: 0.02em; }
.two-col { columns: 2; column-gap: 4mm; }
.two-col li { break-inside: avoid; }

/* ---- challenges ---- */
.challenges { display: flex; gap: 2.5mm; margin-top: 4.5mm; }
.challenge {
  flex: 1; background: var(--color-card-bg); border-radius: 0.65mm;
  box-shadow: 0 0 0 0.25mm var(--color-border-card); overflow: hidden;
}
.challenge header {
  position: relative; display: flex; align-items: baseline; gap: 1mm;
  background: var(--color-banner);
  color: var(--color-banner-text); padding: 1.1mm 1.6mm 1.2mm;
}
.challenge .dice {
  font-family: "Noto Sans", sans-serif; font-weight: 800; font-size: 7.6pt;
}
.challenge .sep { opacity: 0.8; font-weight: 300; }
.challenge h2 {
  margin: 0; font-size: 8.3pt; font-variant: small-caps; font-weight: 800;
  letter-spacing: 0.03em; white-space: nowrap;
}
.challenge header::before {  /* left rivet */
  content: ""; position: absolute; right: 2.4mm; bottom: -0.9mm;
  width: 1.8mm; height: 1.8mm; border-radius: 50%;
  background: var(--color-card-solid);
  border: 0.25mm solid var(--color-banner);
}
.challenge header::after {  /* right rivet */
  content: ""; position: absolute; right: 0.1mm; bottom: -0.9mm;
  width: 1.8mm; height: 1.8mm; border-radius: 50%;
  background: var(--color-card-solid);
  border: 0.25mm solid var(--color-banner);
}
.challenge ul { margin: 1mm 1.2mm 0; font-size: 8.8pt; padding-bottom: 0.8mm;
  border-bottom: 0.25mm solid var(--color-border-challenge-light); }
.challenge li { padding-left: 3.2mm; }
.traits { font-style: italic; }
.moves { font-variant: small-caps; font-weight: 600; letter-spacing: 0.02em; }
.challenge .fail {
  margin: 0.9mm 1.2mm 1.2mm; padding-left: 3.2mm; position: relative;
  font-style: italic; font-size: 8.6pt; font-weight: 700;
}
.challenge .fail::before {
  position: absolute; left: 0.2mm; top: 0.08em;
  font-family: "DejaVu Sans", sans-serif; line-height: 1;
}

/* ---- mix it up ---- */
.mix-it-up {
  display: flex; align-items: center; gap: 2.4mm; margin: 4.5mm 0 0;
  background: var(--color-card-bg); border-radius: 0.6mm; padding: 1mm 1.6mm;
  box-shadow: 0 0 0 0.25mm var(--color-border-card);
}
.mix-it-up strong {
  background: var(--color-dice-bg); color: var(--color-heading); font-variant: small-caps; font-weight: 700;
  letter-spacing: 0.05em; border-radius: 0.45mm; padding: 0.3mm 1.8mm 0.4mm;
  white-space: nowrap;
}
.mix-it-up em { font-size: 9pt; }
"""

# ---------------------------------------------------------------- template ---

TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="page">
<header class="module-head">
  <div class="module-art">{goblin_icon}</div>
  <h1>{title}</h1>
  {hooks}
  {intros}
</header>
{body}
</div></body></html>
"""

# ------------------------------------------------------------------- main ---


def to_pdf(html_path, pdf_path):
    cmd = [
        "chromium",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--force-color-profile=srgb",
        f"--print-to-pdf={pdf_path}",
        f"file://{Path(html_path).resolve()}",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"chromium failed:\n{res.stderr}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--html", action="store_true", help="keep the intermediate HTML")
    args = ap.parse_args()

    pdf_path = args.output or args.source.with_suffix(".pdf")
    html = render(parse(args.source.read_text(encoding="utf-8")))

    if args.html:
        html_path = args.source.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
    else:
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".html", delete=False, encoding="utf-8"
        )
        tmp.write(html)
        tmp.close()
        html_path = Path(tmp.name)

    to_pdf(html_path, pdf_path)
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
