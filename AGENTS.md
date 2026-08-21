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
| Page Break | `.page-break` | - | Forces the following content to start on a new page |

Outside of fenced divs, a level-2 heading followed by a paragraph becomes a simple paragraph section with an underlined title. See [Simple Paragraphs](#simple-paragraphs) below.

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
- Challenges: `xD | TITLE` (e.g., `4D | Ask One Question`); the pipe may be omitted
- x range: 2 to 8

A `.challenges` div can contain any number of challenge cards (one or more).

### Pressure Pool Links

The pressure pools section contains different pressure pools in columns. They
can have links between them, represented as lines between two columns, with a
different icon on the line:
- Lock link: lock icon
- Trigger link: a right arrow inside a circle

### Simple Paragraphs

A section with an underlined title and a body paragraph is written as a
level-2 heading followed by one or more paragraphs, outside of any fenced div:

```markdown
## Optional Title

Body text goes here.
```

The title is rendered in uppercase with a horizontal rule underneath. Fenced
divs (pressure pools, challenges, etc.) break a simple paragraph section and are
rendered as separate top-level blocks.

Level-3 headings inside a section become bold subheadings:

```markdown
## Action Rolls

Intro paragraph.

### Pick a Stat

The GM picks which stat the action uses.
```

A level-3 heading at the top level starts a new simple paragraph section with a
subheading-style title (no underline). Omitting the heading produces a plain
body paragraph.

### Blockquotes

Lines starting with `>` become a quote block: italic text with a rule down the
left edge. Use it for asides aimed at the GM, such as a cue to roll a pressure
pool or a list of adversary stat lines.

```markdown
> 6D | Mama Troll (Elite Brute)
> 4D Fistons Trolls (Tough Blaster)
```

Adjacent `>` lines form a single quote block and each keeps its own line. A
line right after a quote that omits the `>` is a lazy continuation and is
appended to the preceding line. A blank line ends the quote.

Quotes work in section bodies, not in the module header: a `>` line before the
first heading renders as a normal hook or intro paragraph.

### Page Breaks

A manual page break is inserted with an empty `.page-break` fenced div:

```markdown
::: {.page-break}
:::
```

This is useful to keep a challenge panel or pressure pool from being split
across two pages. A break with nothing before or after it is dropped rather
than emitting a blank page, and a run of consecutive breaks counts as one.

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
→ headless Chromium `--print-to-pdf`. Requires `markdown-it-py`, a
`chromium` binary and `pdfinfo` (poppler) for page numbering. `--html` keeps
the intermediate HTML next to the source for debugging; it is a build artifact
and is not tracked. Page size: 176mm × 250mm.

Every page is full-bleed. Chromium never paints into an `@page` margin, so the
margin stays 0 and the parchment is drawn by one backdrop element per page,
which also keeps each page's gradient identical instead of stretching one
gradient over the whole document.

Page numbers need the page count, so a module that overflows is rendered
twice: the first PDF is measured with `pdfinfo`, and if it holds more than one
page the HTML is rendered again with one bottom-centered number per page,
absolutely positioned at each page boundary. Content is kept out of that strip
by a repeating table footer, the one construct Chromium both repeats on every
page and reserves room for; a matching header row gives every continuation page
its top margin, which the block padding alone only applies to the first page.
Reserving that room can push content onto one more page, so the render repeats
until the page count settles.

A single-page module is left alone: no number, no reserved strip. When
`pdfinfo` (poppler) is missing, numbering is skipped with a warning and pages
past the first fall back to a flat parchment colour.
