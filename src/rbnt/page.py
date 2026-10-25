"""Render the report's content blocks to the web page."""

from html import escape

from . import htmlkit as H

NAV = [("glance", "At a glance"), ("where", "Who holds RBNT"), ("size", "Holders by size"),
       ("concentration", "Concentration"), ("largest", "Largest holders"), ("staking", "Staking"),
       ("named", "Named wallets"), ("method", "Method"), ("data", "Data"), ("words", "Words used")]


def block_html(b):
    kind = b[0]
    if kind == "section":
        return None  # handled by the caller
    if kind == "h3":
        return f"<h3>{escape(b[1])}</h3>"
    if kind == "answer":
        return f'<p class="answer">{b[1]}</p>'
    if kind == "p":
        return f"<p>{b[1]}</p>"
    if kind == "list":
        return "<ul>" + "".join(f"<li>{x}</li>" for x in b[1]) + "</ul>"
    if kind == "glance":
        return '<div class="glance">' + "".join(f"<article><h3>{escape(h)}</h3><p>{t}</p></article>" for h, t in b[1]) + "</div>"
    if kind == "plain":
        return f'<div class="plain"><p class="label">{escape(b[1])}</p><p>{b[2]}</p></div>'
    if kind == "notice":
        return '<div class="notice">' + "".join(f"<p>{x}</p>" for x in b[1]) + "</div>"
    if kind == "fig":
        _, num, title, sub, chart, source, tbl = b
        table_html = H.table(*tbl) if tbl else ""
        return H.figure(num, title, sub, chart, source, table_html)
    if kind == "table":
        return H.table(b[1], b[2], b[3] if len(b) > 3 else None, cls=b[4] if len(b) > 4 else "")
    if kind == "rawtable":
        return b[1]
    if kind == "check":
        return f'<div class="check"><p class="label">Check it yourself</p><pre>{escape(b[1])}</pre></div>'
    if kind == "two":
        return '<div class="two">' + "".join(block_html(x) for x in b[1]) + "</div>"
    if kind == "downloads":
        return ('<div class="dl">' + "".join(f'<a href="{href}"><b>{escape(t)}</b><span>{escape(d)}</span></a>'
                                             for t, d, href in b[1]) + "</div>"
                + '<div class="print-only"><ul>' + "".join(f"<li>{escape(t)}: <code>{escape(href)}</code></li>"
                                                           for t, d, href in b[1]) + "</ul></div>")
    if kind == "gloss":
        return '<dl class="gloss">' + "".join(f"<dt>{escape(t)}</dt><dd>{d}</dd>" for t, d in b[1]) + "</dl>"
    raise ValueError(kind)


def render(blocks, hero, meta):
    """hero: dict(title, lede, eyebrow, tiles=[(value, unit, label, delta)], meta_line)."""
    sections, cur = [], None
    for b in blocks:
        if b[0] == "section":
            cur = {"id": b[3], "label": b[1], "title": b[2], "body": []}
            sections.append(cur)
        else:
            cur["body"].append(block_html(b))
    body = "".join(
        f'<section class="s" id="{s["id"]}"><p class="label">{escape(s["label"])}</p><h2>{escape(s["title"])}</h2>'
        + "".join(s["body"]) + "</section>" for s in sections)
    tiles = "".join(
        f'<div class="tile"><div class="v">{escape(v)}<small>{escape(u)}</small></div><div class="k">{escape(k)}</div>'
        f'<div class="d">{d}</div></div>' for v, u, k, d in hero["tiles"])
    toc = "".join(f'<li><a href="#{i}">{escape(t)}</a></li>' for i, t in NAV)
    from .svgcharts import CSS as chart_css
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(meta["title"])}</title>
<meta name="description" content="{escape(meta["description"])}">
<meta property="og:title" content="{escape(meta["title"])}">
<meta property="og:description" content="{escape(meta["description"])}">
<meta property="og:image" content="community/og_1200x630.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/icon.png">
<link rel="preload" href="assets/fonts/be-vietnam-pro-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/site.css">
<style>{chart_css}</style>
<script>try{{var t=localStorage.getItem("rbnt-theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#main">Skip to the report</a>
<header class="bar">
  <div class="wrap">
    <a class="brand" href="#top"><img src="brand/logos/dao-logo-on-dark.png" alt="Redbelly DAO">RBNT Holder Report <span>{escape(meta["edition"])}</span></a>
    <nav aria-label="Report">
      <span class="links"><a href="#glance">Summary</a><a href="#staking">Staking</a><a href="#named">Named wallets</a><a href="#method">Method</a><a href="#data">Data</a></span>
      <button id="theme" type="button">Dark theme</button>
      <a class="primary" href="{meta["pdf"]}">PDF</a>
    </nav>
  </div>
</header>
<div class="hero" id="top">
  <div class="wrap">
    <img class="print-only hero-logo" src="brand/logos/dao-logo-on-dark.png" alt="Redbelly DAO">
    <p class="eyebrow"><span><span class="dot"></span>{escape(hero["eyebrow"])}</span></p>
    <h1>{escape(hero["title"])}</h1>
    <p class="lede">{hero["lede"]}</p>
    <div class="tiles">{tiles}</div>
    <p class="meta">{hero["meta_line"]}</p>
  </div>
</div>
<div class="wrap layout">
  <aside class="toc" aria-label="Contents"><p>Contents</p><ol>{toc}</ol></aside>
  <main id="main">{body}
  <footer class="foot">{meta["footer"]}</footer>
  </main>
</div>
<script src="assets/site.js" defer></script>
</body>
</html>
"""
