"""Turn the report's content blocks into the web page.

Block kinds: chapter, lead, text, bullets, findings, rules, terms, chart, grid,
raw, tryit, files, glossary, aside.
"""

from html import escape

from .drawing import STYLE as CHART_STYLE
from .edition import HOME


def grid_html(head, rows, mono_cols=None, total=None, css=""):
    mono_cols = set(range(1, len(head))) if mono_cols is None else mono_cols
    cell = lambda i, v, tag: (f'<{tag} class="r">{v}</{tag}>' if i in mono_cols else f"<{tag}>{v}</{tag}>")
    thead = "".join(cell(i, escape(str(h)), "th") for i, h in enumerate(head))
    body = "".join("<tr>" + "".join(cell(i, v, "td") for i, v in enumerate(r)) + "</tr>" for r in rows)
    if total:
        body += '<tr class="sum">' + "".join(cell(i, v, "td") for i, v in enumerate(total)) + "</tr>"
    return f'<div class="grid-wrap"><table class="{css}"><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table></div>'


def chart_html(number, title, note, name, provenance, csv_file, grid=None):
    svg = (HOME / "figures" / f"{name}.svg").read_text()
    tools = f'<a class="tool" href="{csv_file}" download>CSV</a>' if csv_file else ""
    table = ""
    if grid:
        tools = '<button class="tool" type="button" data-toggle>Table</button>' + tools
        table = f'<div class="as-table" hidden>{grid_html(*grid)}</div>'
    return (f'<figure class="chart" id="chart-{number}"><div class="chart-top"><div><span class="chart-no">Chart {number}</span>'
            f'<h4>{escape(title)}</h4></div><div class="tools">{tools}</div></div>'
            f'<p class="note">{note}</p><div class="canvas">{svg}</div>{table}'
            f'<figcaption><b>Read from</b> {provenance}</figcaption></figure>')


def block(b):
    kind = b[0]
    if kind == "lead":
        return f'<p class="lead"><span>Short answer</span>{b[1]}</p>'
    if kind == "text":
        return f"<p>{b[1]}</p>"
    if kind == "h3":
        return f"<h3>{escape(b[1])}</h3>"
    if kind == "bullets":
        return "<ul>" + "".join(f"<li>{x}</li>" for x in b[1]) + "</ul>"
    if kind == "findings":
        return '<ol class="findings">' + "".join(
            f'<li><div class="big">{escape(v)}</div><div><h3>{escape(t)}</h3><p>{d}</p></div></li>' for v, t, d in b[1]) + "</ol>"
    if kind == "rules":
        return '<div class="rules">' + "".join(f"<div><b>{escape(t)}</b><p>{d}</p></div>" for t, d in b[1]) + "</div>"
    if kind == "terms":
        return ('<div class="terms"><p class="kicker">Three terms used throughout</p><dl>' +
                "".join(f"<dt>{escape(t)}</dt><dd>{d}</dd>" for t, d in b[1]) + "</dl></div>")
    if kind == "aside":
        return f'<aside class="aside"><p class="kicker">{escape(b[1])}</p><p>{b[2]}</p></aside>'
    if kind == "chart":
        return chart_html(*b[1:])
    if kind == "grid":
        return grid_html(*b[1:])
    if kind == "raw":
        return b[1]
    if kind == "tryit":
        return f'<div class="tryit"><p class="kicker">Try it yourself</p><p>{b[1]}</p><pre>{escape(b[2])}</pre></div>'
    if kind == "files":
        cards = "".join(f'<a href="{href}"><span>{escape(kind_)}</span><b>{escape(title)}</b></a>' for title, kind_, href in b[1])
        listing = "".join(f"<li>{escape(title)}: <code>{escape(href)}</code></li>" for title, _, href in b[1])
        return f'<div class="files">{cards}</div><ul class="print-list">{listing}</ul>'
    if kind == "glossary":
        return grid_html(["Term", "What it means here"], [[f"<b>{escape(t)}</b>", d] for t, d in b[1]], set(), css="gloss")
    raise ValueError(kind)


def page(blocks, top, meta):
    chapters, current = [], None
    for b in blocks:
        if b[0] == "chapter":
            current = {"no": b[1], "title": b[2], "id": b[3], "short": b[4], "html": []}
            chapters.append(current)
        else:
            current["html"].append(block(b))
    body = "".join(
        f'<section class="chapter" id="{c["id"]}"><header class="chapter-head">'
        f'<span class="chapter-no">{escape(c["no"])}</span><h2>{escape(c["title"])}</h2></header>{"".join(c["html"])}</section>'
        for c in chapters)
    chips = "".join(f'<a href="#{c["id"]}">{escape(c["short"])}</a>' for c in chapters)
    board = grid_html(["", top["board_head"][0], top["board_head"][1], "Change"], top["board"], {1, 2, 3}, css="board")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(meta["title"])}</title>
<meta name="description" content="{escape(meta["description"])}">
<meta property="og:title" content="{escape(meta["title"])}">
<meta property="og:description" content="{escape(meta["description"])}">
<meta property="og:image" content="community/card-discord.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/icon.png">
<link rel="stylesheet" href="assets/holders.css">
<style>{CHART_STYLE}</style>
<script>try{{var m=localStorage.getItem("holders-mode");if(m)document.documentElement.dataset.mode=m}}catch(e){{}}</script>
</head>
<body>
<a class="jump" href="#content">Go to the report</a>
<header class="topbar">
  <div class="inner">
    <a class="mark" href="#"><img src="brand/logos/dao-logo-on-dark.png" alt="Redbelly DAO"><span>RBNT holders <em>{escape(meta["edition"])}</em></span></a>
    <nav aria-label="Main">
      <a class="wide-only" href="#{chapters[0]["id"]}">Findings</a>
      <a class="wide-only" href="how-we-did-it.html">How we did it</a>
      <a class="wide-only" href="#files">Data</a>
      <button type="button" id="mode">Dark</button>
      <a class="cta" href="{meta["pdf"]}">PDF</a>
    </nav>
  </div>
</header>
<div class="opening">
  <div class="inner opening-grid">
    <div>
      <img class="print-logo" src="brand/logos/dao-logo-on-dark.png" alt="Redbelly DAO">
      <p class="overline">{escape(top["overline"])}</p>
      <h1>{escape(top["title"])}</h1>
      <p class="sub">{top["sub"]}</p>
      <p class="blocks">{top["blocks"]}</p>
    </div>
    <div class="scoreboard"><p class="kicker">The quarter in numbers</p>{board}<p class="checked">{top["checked"]}</p></div>
  </div>
</div>
<nav class="chips inner" aria-label="Chapters">{chips}</nav>
<main id="content" class="inner">{body}
<footer class="closing">{meta["footer"]}</footer>
</main>
<script src="assets/holders.js" defer></script>
</body>
</html>
"""


def doc_page(title, body_html, meta):
    """A plain document page (how-we-did-it.html) in the same look."""
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><link rel="icon" href="assets/icon.png"><link rel="stylesheet" href="assets/holders.css">
<script>try{{var m=localStorage.getItem("holders-mode");if(m)document.documentElement.dataset.mode=m}}catch(e){{}}</script>
</head>
<body>
<header class="topbar"><div class="inner"><a class="mark" href="index.html"><img src="brand/logos/dao-logo-on-dark.png" alt="Redbelly DAO"><span>RBNT holders <em>{escape(meta["edition"])}</em></span></a>
<nav aria-label="Main"><a href="index.html">Report</a><button type="button" id="mode">Dark</button><a class="cta" href="{meta["pdf"]}">PDF</a></nav></div></header>
<main class="inner prose">{body_html}<footer class="closing">{meta["footer"]}</footer></main>
<script src="assets/holders.js" defer></script>
</body>
</html>
"""
