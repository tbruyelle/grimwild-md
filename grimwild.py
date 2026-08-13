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

# ---------------------------------------------------------------- parsing ---

DIV_OPEN = re.compile(r"^:::\s*\{([^}]*)\}\s*$")
DICE_POOL = re.compile(r"^(\dD)\s+(.*)$")
DICE_CHAL = re.compile(r"^(\dD)\s*\|\s*(.*)$")
LINK = re.compile(r"^(.*?)\s*(--\*->|-->)\s*(.*?)$")


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
                    "from": m.group(1),
                    "to": m.group(3),
                    "type": "trigger" if "*" in m.group(2) else "lock",
                }
            else:
                print(f"warning: unparsed line in pressure pool: {s!r}",
                      file=sys.stderr)
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
                    {"dice": m.group(1), "title": m.group(2),
                     "traits": [], "moves": [], "fail": None}
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
            mod["blocks"].append(parse_div(m.group(1), inner))
            continue
        if line.startswith("# "):
            mod["title"] = line[2:].strip()
            i += 1
            continue
        para = [line.strip()]
        i += 1
        while (i < len(lines) and lines[i].strip()
               and not DIV_OPEN.match(lines[i]) and not lines[i].startswith("# ")):
            para.append(lines[i].strip())
            i += 1
        mod["blocks"].append({"kind": "paragraph", "text": " ".join(para)})
    return mod

# ------------------------------------------------------------------ icons ---

# Item markers are Unicode glyphs rendered with DejaVu Sans (the font that
# covers them all, so they share metrics and print at a uniform size).
MARKER_CHARS = {
    "dot": "\u25c9",      # ◉ fisheye (pools, moves)
    "triangle": "\u25b8", # ▸ (useful pieces)
    "box": "\u25a2",      # ▢ (set it up)
    "star": "\u2731",     # ✱ (traits)
    "cross": "\u2718",    # ✘ (fail state)
}


def icon_svg(kind, color="#8e877f"):
    """Inline SVG icons for pool properties and links."""
    if kind == "lock":
        return (f"<svg viewBox='0 0 10 10'><rect x='2' y='4.4' width='6' height='4.4' rx='1' fill='{color}'/>"
                f"<path d='M3.2 4.4 V3.1 a1.8 1.8 0 0 1 3.6 0 V4.4' fill='none' "
                f"stroke='{color}' stroke-width='1.2'/></svg>")
    if kind == "trigger":
        return (f"<svg viewBox='0 0 10 10'><circle cx='5' cy='5' r='3.9' fill='#f4eee0' "
                f"stroke='{color}' stroke-width='1.2'/>"
                f"<path d='M3.9 2.9 L6.1 5 L3.9 7.1' fill='none' stroke='{color}' "
                f"stroke-width='1.2' stroke-linecap='round'/></svg>")
    if kind == "repeat":
        return (f"<svg viewBox='0 0 10 10'><path d='M8.8 3.4 A3.7 3.7 0 1 0 9.2 5.6' "
                f"fill='none' stroke='{color}' stroke-width='1.3' stroke-linecap='round'/>"
                f"<path d='M8.9 0.9 L8.8 3.5 L6.6 2.2 Z' fill='{color}'/></svg>")
    if kind == "end":
        return (f"<svg viewBox='0 0 10 10'><circle cx='5' cy='5' r='4' fill='#f4eee0' "
                f"stroke='{color}' stroke-width='1.2'/>"
                f"<path d='M5 1.6 L5.85 3.75 L8.1 3.8 L6.35 5.3 L7.1 7.6 L5 6.3 L2.9 7.6 "
                f"L3.65 5.3 L1.9 3.8 L4.15 3.75 Z' fill='{color}'/></svg>")
    return ""


# --------------------------------------------------------------- rendering ---

def inline(text):
    return MD.renderInline(text.strip())


def render_pool(pool):
    classes = " ".join(["pool"] + pool["props"])
    prop_icon = ""
    if "repeat" in pool["props"]:
        prop_icon = f"<span class='prop'>{icon_svg('repeat')}</span>"
    elif "end" in pool["props"]:
        prop_icon = f"<span class='prop'>{icon_svg('end')}</span>"
    items = "".join(f"<li>{inline(i)}</li>" for i in pool["items"])
    html = (
        f"<div class='{classes}'>"
        f"<header><span class='dice'>{pool['dice']}</span>"
        f"<h2>{inline(pool['title'])}</h2>{prop_icon}</header>"
        f"<ul class='m-dot'>{items}</ul></div>"
    )
    if pool["link"]:
        html += (f"<div class='pool-link {pool['link']['type']}'>"
                 f"{icon_svg(pool['link']['type'])}</div>")
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
        out.append(f"<div class='group'>{lead}<ul class='{marker} {cls}'>{items}</ul></div>")
    return (f"<section class='banded {kind}'><h2 class='banner'>{title}</h2>"
            f"<div class='cols'>{''.join(out)}</div></section>")


def render_challenges(challenges):
    out = []
    for c in challenges:
        traits = "".join(f"<li>{inline(t)}</li>" for t in c["traits"])
        moves = "".join(f"<li>{inline(m)}</li>" for m in c["moves"])
        fail = ""
        if c["fail"]:
            fail_text = re.sub(r"^(\dD)\s+", r"<span class='dice-text'>\1</span> ",
                               c["fail"])
            fail = f"<p class='fail'>{inline(fail_text)}</p>"
        out.append(
            f"<div class='challenge'>"
            f"<header><span class='dice'>{c['dice']}</span>"
            f"<span class='sep'>|</span><h2>{inline(c['title'])}</h2></header>"
            f"<ul class='m-star traits'>{traits}</ul>"
            f"<ul class='m-dot moves'>{moves}</ul>{fail}</div>"
        )
    return f"<section class='challenges'>{''.join(out)}</section>"


def render(mod):
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
            body_parts.append(render_banded("useful-pieces", "Useful Pieces",
                                            b["groups"], "m-triangle"))
        elif b["kind"] == "setup":
            seen_section = True
            body_parts.append(render_banded("set-it-up", "Set It Up",
                                            b["groups"], "m-box"))
        elif b["kind"] == "challenges":
            seen_section = True
            body_parts.append(render_challenges(b["challenges"]))
    flush_pools()

    hooks = "".join(h for h in head_parts if "class='hook'" in h)
    intros = "".join(h for h in head_parts if "class='intro'" in h)
    return TEMPLATE.format(
        title=inline(mod["title"] or ""),
        hooks=f"<div class='hooks'>{hooks}</div>" if hooks else "",
        intros=intros,
        body="\n".join(body_parts),
        css=build_css(),
    )


# -------------------------------------------------------------------- CSS ---

def build_css():
    sizes = {"dot": "0.95em", "triangle": "0.95em", "box": "0.95em",
             "star": "0.82em", "cross": "1.05em"}
    markers_css = ""
    for sel, key in [("ul.m-dot li", "dot"), ("ul.m-triangle li", "triangle"),
                     ("ul.m-box li", "box"), ("ul.m-star li", "star"),
                     (".challenge .fail", "cross")]:
        markers_css += f"""
{sel}::before {{ content: "{MARKER_CHARS[key]}"; font-size: {sizes[key]}; }}"""
    return BASE_CSS.replace("/*MARKERS*/", markers_css)


BASE_CSS = """
@page { size: 176mm 250mm; margin: 0; }
* { box-sizing: border-box; print-color-adjust: exact; -webkit-print-color-adjust: exact; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Noto Serif", serif;
  font-size: 8pt; line-height: 1.22; color: #211d15;
  background:
    radial-gradient(115% 85% at 50% 42%, rgba(0,0,0,0) 52%, rgba(84,70,48,0.27) 100%),
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.42 0 0 0 0 0.38 0 0 0 0 0.30 0 0 0 0.05 0'/></filter><rect width='240' height='240' filter='url(%23n)'/></svg>"),
    linear-gradient(165deg, #efe9d8 0%, #e9e2cf 38%, #ddd3bd 72%, #cfc3aa 100%);
  width: 176mm; height: 250mm; overflow: hidden;
}
.page { padding: 8mm 10.5mm 7mm; height: 100%; }

/* ---- module header ---- */
.module-head {
  position: relative; border: 0.45mm solid rgba(52,45,33,0.65);
  border-radius: 2mm; padding: 2.2mm 4mm 2.6mm; margin-top: 4.5mm;
  background: rgba(246,241,230,0.55);
}
.module-art {
  position: absolute; top: -4.6mm; left: 4mm; width: 15mm; height: 15mm;
  background: linear-gradient(160deg, #3a352c, #232019);
  border-radius: 1.6mm; box-shadow: 0.4mm 0.4mm 0.8mm rgba(30,25,15,0.35);
}
.module-art::after {  /* placeholder glyph for module art */
  content: ""; position: absolute; inset: 3mm;
  background: #efe9d8; border-radius: 50% 50% 46% 46%;
  clip-path: polygon(50% 0, 100% 22%, 86% 100%, 14% 100%, 0 22%);
  opacity: 0.9;
}
h1 {
  font-family: "Noto Sans", sans-serif; font-weight: 800; text-transform: uppercase;
  text-align: center; font-size: 17pt; letter-spacing: 0.015em;
  margin: 0.4mm 0 2mm; color: #16130d;
}
.hooks { display: flex; margin: 0 2mm 1.8mm; }
.hook {
  flex: 1; margin: 0; padding: 0 3mm; font-style: italic; font-size: 7.6pt;
  color: #6d675a; text-align: center;
}
.hook + .hook { border-left: 0.25mm solid rgba(60,50,35,0.30); }
.intro { margin: 0; text-align: justify; font-size: 8.2pt; }
.intro strong { font-variant: small-caps; letter-spacing: 0.02em; }

/* ---- generic lists with Unicode markers ---- */
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
  gap: 6.5mm; margin: 3.5mm 0 0;
}
.pool {
  flex: 1; background: rgba(247,242,231,0.72); border-radius: 1.4mm;
  box-shadow: 0 0 0 0.25mm rgba(80,70,52,0.25);
}
.pool header {
  display: flex; align-items: center; gap: 1.7mm;
  background: linear-gradient(180deg, #ddd7ca, #c9c2b1);
  border-radius: 1.3mm; padding: 1mm 1.5mm;
  box-shadow: 0 0 0 0.25mm rgba(80,70,52,0.30);
}
.pool .dice {
  font-family: "Noto Sans", sans-serif; font-weight: 800; font-size: 7.6pt;
  background: #2c2721; color: #f4eee0; border-radius: 0.9mm;
  padding: 0.15mm 1.1mm; letter-spacing: 0.02em;
}
.pool h2 {
  margin: 0; font-size: 9pt; font-variant: small-caps; font-weight: 700;
  letter-spacing: 0.025em; color: #221e15; white-space: nowrap;
}
.pool .prop { margin-left: auto; width: 4mm; height: 4mm; }
.pool .prop svg { width: 100%; height: 100%; display: block; }
.pool ul { padding: 1.1mm 1.5mm 1.3mm; }
.pool-link {
  position: relative; flex: none; align-self: flex-start;
  width: 6.5mm; height: 6mm; margin: 0 -6.5mm;  /* exactly bridges the flex gap */
}
.pool-link::before {  /* line at header middle, spanning the gap only */
  content: ""; position: absolute; left: 0; right: 0; top: 2.6mm;
  border-top: 0.3mm solid #9a9078;
}
.pool-link svg {  /* centered on the line, backing hides the line crossing */
  position: relative; display: block; width: 3.5mm; height: 3.5mm;
  margin: 0.85mm auto 0; background: #e9e3d2; border-radius: 50%;
}

/* ---- banded sections (Useful Pieces / Set It Up) ---- */
.banded {
  margin-top: 3.5mm; border-radius: 1.6mm; overflow: hidden;
  box-shadow: 0 0 0 0.3mm rgba(80,70,52,0.45);
}
.banner {
  margin: 0; text-align: center; font-size: 9.5pt; font-variant: small-caps;
  font-weight: 700; letter-spacing: 0.07em; color: #231f16;
  background: linear-gradient(180deg, #b3a897, #9d927f);
  padding: 0.9mm 0 1.1mm;
}
.cols { display: flex; background: rgba(247,242,231,0.78); }
.group { flex: 1; padding: 1.5mm 2mm 1.7mm; }
.group + .group { border-left: 0.25mm solid rgba(60,50,35,0.22); }
.lead { margin: 0 0 0.8mm; text-align: left; }
.lead strong { font-variant: small-caps; letter-spacing: 0.02em; }
.two-col { columns: 2; column-gap: 4mm; }
.two-col li { break-inside: avoid; }

/* ---- challenges ---- */
.challenges { display: flex; gap: 2.5mm; margin-top: 3.5mm; }
.challenge {
  flex: 1; background: rgba(247,242,231,0.72); border-radius: 1.3mm;
  box-shadow: 0 0 0 0.25mm rgba(80,70,52,0.25); overflow: hidden;
}
.challenge header {
  position: relative; display: flex; align-items: baseline; gap: 1mm;
  background: linear-gradient(180deg, #ada292, #998e7a);
  color: #f6f1e4; padding: 1.1mm 1.6mm 1.2mm;
}
.challenge .dice {
  font-family: "Noto Sans", sans-serif; font-weight: 800; font-size: 7.6pt;
}
.challenge .sep { opacity: 0.75; font-weight: 300; }
.challenge h2 {
  margin: 0; font-size: 8.3pt; font-variant: small-caps; font-weight: 700;
  letter-spacing: 0.03em; white-space: nowrap;
}
.challenge header::after {  /* rivets */
  content: ""; position: absolute; right: 1.4mm; bottom: -0.9mm;
  width: 2mm; height: 2mm; border-radius: 50%;
  background: #e6e0d2; box-shadow: -2.9mm 0 0 #e6e0d2,
  inset -0.2mm -0.2mm 0.4mm rgba(60,50,35,0.4);
}
.challenge ul { margin: 1mm 1.2mm 0; font-size: 7.7pt; }
.challenge li { padding-left: 3.2mm; }
.traits { font-style: italic; }
.moves { font-variant: small-caps; font-weight: 600; letter-spacing: 0.02em; }
.challenge .fail {
  margin: 0.9mm 1.2mm 1.2mm; padding-left: 3.2mm; position: relative;
  font-style: italic; font-size: 7.7pt;
}
.challenge .fail .dice-text {
  font-style: normal; font-weight: 700; text-transform: lowercase;
}
.challenge .fail::before {
  position: absolute; left: 0.2mm; top: 0.08em;
  font-family: "DejaVu Sans", sans-serif; font-size: 0.95em; line-height: 1;
}

/* ---- mix it up ---- */
.mix-it-up {
  display: flex; align-items: center; gap: 2.4mm; margin: 3.5mm 0 0;
  background: rgba(247,242,231,0.72); border-radius: 1.2mm; padding: 1mm 1.6mm;
  box-shadow: 0 0 0 0.25mm rgba(80,70,52,0.25);
}
.mix-it-up strong {
  background: #4c4636; color: #f4eee0; font-variant: small-caps; font-weight: 700;
  letter-spacing: 0.05em; border-radius: 0.9mm; padding: 0.3mm 1.8mm 0.4mm;
  white-space: nowrap;
}
.mix-it-up em { font-size: 9pt; }
"""

# ---------------------------------------------------------------- template ---

TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="page">
<header class="module-head">
  <div class="module-art"></div>
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
        "chromium", "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", "--force-color-profile=srgb",
        f"--print-to-pdf={pdf_path}", f"file://{Path(html_path).resolve()}",
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
        tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                          encoding="utf-8")
        tmp.write(html)
        tmp.close()
        html_path = Path(tmp.name)

    to_pdf(html_path, pdf_path)
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
