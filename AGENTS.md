# Grimwild MD

Generate PDFs like example-golden.pdf from markdown file, using custom syntax
for the specific sections.

## Markdown Syntax

Custom syntax built on fenced divs (`:::`) with these section types:

| Section | Div Class | Rendered Prefix | Notes |
|---------|-----------|-----------------|-------|
| Module Icon | `.module-icon` | - | Optional SVG icon for the module header. Defaults to a goblin mask if omitted. Good source for icons: https://game-icons.net/ |
| Pressure Pools | `.pressure-pool` | `◉` | Tables for columns; links: `>> B` (lock), `>>* B` (trigger) |
| Pressure Pool properties | `repeat`, `end` | - | Add to div class: `{.pressure-pool repeat}` |
| Useful Pieces | `.useful-pieces` | `▸` | Right-pointing triangle |
| Set It Up | `.set-it-up` | `▢` | Square checkbox |
| Challenges | `.challenges` | by list marker | Traits: `*` (`✱`), Moves: `-` (`◉`), Fail State: `x` (`✘`) |

Item prefixes are NOT written in the source. The converter renders the
correct icon from context: div class for pools/pieces/setup, list marker
for challenges. Source items are plain markdown lists; a fail state is a
plain line starting with `x `. Blank lines between challenge groups are
optional, except before the `x ` fail-state line, where one is required
(otherwise markdown parses it as part of the last list item).

Section titles are NOT written in the source either. The converter
renders the banner from the div class: `.useful-pieces` → "Useful
Pieces", `.set-it-up` → "Set It Up".

### Dice Notation

- Pressure Pools: `xD TITLE` (e.g., `4D Night Falls`)
- Challenges: `xD | TITLE` (e.g., `4D | Ask One Question`)
- x range: 2 to 8

### Pressure Pool Links

The pressure pools section contains different pressure pool in columns, they
can have links between them, they are represented as line between 2 columns,
with different icon upon the line:
- Lock link: lock icon
- Trigger link: `a right arrow inside a circle

## File Structure

- `*.md` - Module source files
- `grimwild.py` - Converter (module md → PDF)
- `example-golden.pdf` - Example page with actual text for syntax reference
- `*.pdf` - Generated module pages

## Building

```
python3 grimwild.py <module.md> [-o output.pdf] [--html]
```

Pipeline: custom markdown → HTML (semantic sections, inline SVG icons)
→ headless Chromium `--print-to-pdf`. Requires `markdown-it-py` and a
`chromium` binary. `--html` keeps the intermediate HTML next to the
source for debugging. Page size: 176mm × 250mm, single page.
