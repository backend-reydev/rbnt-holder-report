"""Helpers for writing the report pages: tables, figures and number formats."""

import csv
from html import escape

from . import config


def n0(v):
    return f"{v:,.0f}"


def mil(v, d=1):
    """Plain-language size: 751.3 million, 500 million, 1.74 billion, 12,345, 5.84."""
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:,.2f} billion"
    if a >= 1e6:
        x = f"{v / 1e6:,.{d}f}"
        return (x[:-2] if x.endswith(".0") else x) + " million"
    if a >= 100:
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def signed(v, f=n0):
    return ("+" if v > 0 else "") + f(v)


def pct(v, d=1):
    return f"{v:.{d}f}%"


def read_csv(name):
    with open(config.data_dir("processed") / name) as f:
        return list(csv.DictReader(f))


def table(header, rows, numeric=None, cls="", total=None, caption=None):
    """numeric: set of column indexes to right-align in mono."""
    numeric = numeric if numeric is not None else set(range(1, len(header)))
    h = "".join(f'<th class="n">{escape(x)}</th>' if i in numeric else f"<th>{escape(x)}</th>" for i, x in enumerate(header))
    body = []
    for r in rows:
        body.append("<tr>" + "".join(
            f'<td class="n">{escape(str(x))}</td>' if i in numeric else f"<td>{x}</td>" for i, x in enumerate(r)) + "</tr>")
    if total:
        body.append('<tr class="total">' + "".join(
            f'<td class="n">{escape(str(x))}</td>' if i in numeric else f"<td>{escape(str(x))}</td>"
            for i, x in enumerate(total)) + "</tr>")
    cap = f"<caption class=\"skip\">{escape(caption)}</caption>" if caption else ""
    return f'<div class="tw"><table class="{cls}">{cap}<thead><tr>{h}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def figure(num, title, sub, chart_name, source, table_html=""):
    svg = (config.ROOT / "report" / "charts" / f"{chart_name}.svg").read_text()
    tv = f'<details class="tv"><summary>Show the numbers</summary>{table_html}</details>' if table_html else ""
    return (f'<figure class="fig" id="fig-{num}"><p class="ft">Figure {num}</p><h4>{escape(title)}</h4>'
            f'<p class="sub">{sub}</p><div class="plot">{svg}</div>{tv}'
            f"<figcaption>{source}</figcaption></figure>")
