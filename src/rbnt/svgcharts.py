"""Small SVG chart writer in the Task Board brand.

Charts are plain SVG with CSS classes, so one file serves the web page (light
and dark themes through CSS variables), the PDF and the PNG exports. Every mark
carries a data-tip attribute that the page turns into a hover tooltip, and a
<title> for screen readers and plain viewers.

Colour follows the brand: the accent red marks the series the chart is about,
slate neutrals carry the comparison. Text never takes a series colour.
"""

from html import escape

CSS = """
.chart{font-family:"Be Vietnam Pro",ui-sans-serif,system-ui,sans-serif;font-size:12px}
.chart .grid{stroke:var(--c-grid,#DAE1E7);stroke-width:1}
.chart .axis{stroke:var(--c-axis,#C3CDD4);stroke-width:1}
.chart .tick{fill:var(--c-muted,#596975);font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px}
.chart .lab{fill:var(--c-ink-dim,#394853)}
.chart .lab-strong{fill:var(--c-ink,#0F1A22);font-weight:600}
.chart .val{fill:var(--c-ink,#0F1A22);font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px}
.chart .val-in{fill:#fff;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px}
.chart .s-accent{fill:var(--c-accent,#EF5350)}
.chart .s-muted{fill:var(--c-muted-mark,#596975)}
.chart .s-light{fill:var(--c-light-mark,#C3CDD4)}
.chart .s-dark{fill:var(--c-dark-mark,#1d3140)}
.chart .l-accent{stroke:var(--c-accent,#EF5350);stroke-width:2;fill:none;stroke-linejoin:round;stroke-linecap:round}
.chart .l-muted{stroke:var(--c-muted-mark,#596975);stroke-width:2;fill:none;stroke-linejoin:round;stroke-linecap:round}
.chart .l-ref{stroke:var(--c-axis,#C3CDD4);stroke-width:1;fill:none}
.chart .a-accent{fill:var(--c-accent,#EF5350);opacity:.10}
.chart .a-muted{fill:var(--c-muted-mark,#596975);opacity:.12}
.chart .dot-ring{stroke:var(--c-surface,#fff);stroke-width:2}
.chart .hit{fill:transparent}
.chart .hit-line{stroke:var(--c-muted,#596975);stroke-width:1;opacity:0}
.chart g.col:hover .hit-line{opacity:.6}
.chart [data-tip]:hover{opacity:.85}
.chart .key{fill:var(--c-ink-dim,#394853)}
"""

ACCENT, MUTED, LIGHT, DARK = "s-accent", "s-muted", "s-light", "s-dark"


def fmt_num(v, digits=1):
    """Compact number for ticks and labels: 1.96B, 345.6M, 12.3K, 950."""
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1e9:
        return f"{sign}{a / 1e9:.2f}B" if digits else f"{sign}{a / 1e9:g}B"
    if a >= 1e6:
        return f"{sign}{a / 1e6:.{digits}f}M" if digits else f"{sign}{a / 1e6:g}M"
    if a >= 1e4:
        return f"{sign}{a / 1e3:.{digits}f}K" if digits else f"{sign}{a / 1e3:g}K"
    return f"{sign}{a:,.0f}"


def text_w(s, size=12):
    """Rough rendered width of a label in Be Vietnam Pro."""
    return len(str(s)) * size * 0.56


def fmt_full(v):
    return f"{v:,.0f}"


def fmt_val(v, unit):
    return f"{v:.1f}%" if unit == "%" else f"{fmt_full(v)} {unit}"


def nice_ticks(lo, hi, n=5):
    if hi == lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 10 ** -len(str(int(1 / raw)))
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if (hi - lo) / step <= n:
            break
    start = (lo // step) * step
    ticks, t = [], start
    while t <= hi + step * 0.001:
        ticks.append(round(t, 10))
        t += step
    if ticks[-1] < hi:
        ticks.append(ticks[-1] + step)
    return ticks


class Svg:
    def __init__(self, w, h, title, desc=""):
        self.w, self.h, self.parts = w, h, []
        self.title, self.desc = title, desc

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, cls="lab", anchor="start", size=None, weight=None, baseline="middle"):
        st = []
        if size:
            st.append(f"font-size:{size}px")
        if weight:
            st.append(f"font-weight:{weight}")
        style = f' style="{";".join(st)}"' if st else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}" '
                 f'dominant-baseline="{baseline}"{style}>{escape(str(s))}</text>')

    def rect(self, x, y, w, h, cls, tip=None, r=0, round_end=None):
        """round_end: 'right', 'top', 'left' or None. Rounds only the data end (4px)."""
        w, h = max(w, 0), max(h, 0)
        t = f' data-tip="{escape(tip)}" tabindex="0"' if tip else ""
        title = f"<title>{escape(tip)}</title>" if tip else ""
        if round_end and w > 0 and h > 0:
            rr = min(4, w / 2, h / 2)
            if round_end == "right":
                d = f"M{x:.1f},{y:.1f}h{w - rr:.1f}a{rr},{rr} 0 0 1 {rr},{rr}v{h - 2 * rr:.1f}a{rr},{rr} 0 0 1 -{rr},{rr}h-{w - rr:.1f}z"
            elif round_end == "left":
                d = f"M{x + w:.1f},{y:.1f}h-{w - rr:.1f}a{rr},{rr} 0 0 0 -{rr},{rr}v{h - 2 * rr:.1f}a{rr},{rr} 0 0 0 {rr},{rr}h{w - rr:.1f}z"
            else:  # top
                d = f"M{x:.1f},{y + h:.1f}v-{h - rr:.1f}a{rr},{rr} 0 0 1 {rr},-{rr}h{w - 2 * rr:.1f}a{rr},{rr} 0 0 1 {rr},{rr}v{h - rr:.1f}z"
            self.add(f'<path d="{d}" class="{cls}"{t}>{title}</path>')
        else:
            self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" class="{cls}"{t}>{title}</rect>')

    def line(self, x1, y1, x2, y2, cls):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}"/>')

    def render(self):
        return (f'<svg class="chart" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                f'role="img" aria-label="{escape(self.title)}" xmlns="http://www.w3.org/2000/svg">'
                f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>" + "".join(self.parts) + "</svg>")


def legend(svg, items, x, y):
    """items: [(label, cls)]. Swatch beside text, text in ink."""
    for label, cls in items:
        svg.rect(x, y - 5, 10, 10, cls, r=2)
        svg.text(x + 16, y, label, "key")
        x += 16 + text_w(label) + 24


def hbar_pair(rows, title, unit="RBNT", series=("30 Jun 2026", "30 Sep 2026"), w=760, label_w=230,
              value_fmt=fmt_num, end_note=None):
    """Horizontal bars, two per row (start muted, end accent). rows: [(label, start, end)]."""
    bar, gap, row_gap = 12, 2, 18
    top = 40
    label_w = max(label_w, max(text_w(r[0]) for r in rows) + 20)
    h = top + len(rows) * (2 * bar + gap + row_gap) + 30
    svg = Svg(w, h, title)
    legend(svg, [(series[0], MUTED), (series[1], ACCENT)], label_w, 14)
    vmax = max(max(s, e) for _, s, e in rows) or 1
    ticks = nice_ticks(0, vmax, 4)
    plot_w = w - label_w - 110
    sx = lambda v: label_w + v / ticks[-1] * plot_w
    for t in ticks:
        svg.line(sx(t), top - 6, sx(t), h - 26, "grid")
        svg.text(sx(t), h - 14, value_fmt(t, 0) if value_fmt is fmt_num else value_fmt(t), "tick", "middle")
    y = top
    for label, s, e in rows:
        svg.text(label_w - 10, y + bar + gap / 2, label, "lab", "end")
        svg.rect(label_w, y, sx(s) - label_w, bar, MUTED, f"{label}, {series[0]}: {fmt_val(s, unit)}", round_end="right")
        svg.rect(label_w, y + bar + gap, sx(e) - label_w, bar, ACCENT, f"{label}, {series[1]}: {fmt_val(e, unit)}",
                 round_end="right")
        note = end_note(label, s, e) if end_note else value_fmt(e)
        svg.text(max(sx(e), sx(s)) + 6, y + bar + gap / 2, note, "val")
        y += 2 * bar + gap + row_gap
    svg.line(label_w, top - 6, label_w, h - 26, "axis")
    return svg.render()


def vbar_pair(cats, starts, ends, title, unit="wallets", series=("30 Jun 2026", "30 Sep 2026"), w=760, h=320,
              value_fmt=fmt_num):
    left, right, top, bottom = 56, 16, 36, 54
    svg = Svg(w, h, title)
    legend(svg, [(series[0], MUTED), (series[1], ACCENT)], left, 12)
    vmax = max(max(starts), max(ends)) or 1
    ticks = nice_ticks(0, vmax, 4)
    plot_h = h - top - bottom
    sy = lambda v: top + plot_h - v / ticks[-1] * plot_h
    for t in ticks:
        svg.line(left, sy(t), w - right, sy(t), "grid")
        svg.text(left - 8, sy(t), value_fmt(t, 0) if value_fmt is fmt_num else value_fmt(t), "tick", "end")
    band = (w - left - right) / len(cats)
    bw = min(20, band * 0.3)
    for i, c in enumerate(cats):
        cx = left + band * i + band / 2
        svg.rect(cx - bw - 1, sy(starts[i]), bw, sy(0) - sy(starts[i]), MUTED, f"{c}, {series[0]}: {fmt_full(starts[i])} {unit}",
                 round_end="top")
        svg.rect(cx + 1, sy(ends[i]), bw, sy(0) - sy(ends[i]), ACCENT, f"{c}, {series[1]}: {fmt_full(ends[i])} {unit}",
                 round_end="top")
        svg.text(cx + 1 + bw / 2, sy(ends[i]) - 9, value_fmt(ends[i]), "val", "middle")
        for k, part in enumerate(wrap(c, 14)):
            svg.text(cx, h - bottom + 16 + k * 13, part, "tick", "middle")
    svg.line(left, sy(0), w - right, sy(0), "axis")
    return svg.render()


def wrap(s, n):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > n and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = f"{cur} {wd}".strip()
    lines.append(cur)
    return lines


def lines_chart(xs, series, title, w=760, h=320, y_fmt=fmt_num, unit="RBNT", x_labels=None, areas=None, y_min=None):
    """series: [(label, values, 'accent'|'muted')]. areas: [(values_low, values_high, 'accent'|'muted')]."""
    left, right, top, bottom = 60, 120, 36, 36
    svg = Svg(w, h, title)
    legend(svg, [(lab, ACCENT if c == "accent" else MUTED) for lab, _, c in series], left, 12)
    allv = [v for _, vals, _ in series for v in vals]
    lo = min(allv) if y_min is None else y_min
    hi = max(allv)
    ticks = nice_ticks(lo, hi, 4)
    lo, hi = ticks[0], ticks[-1]
    plot_w, plot_h = w - left - right, h - top - bottom
    sx = lambda i: left + i / (len(xs) - 1) * plot_w
    sy = lambda v: top + plot_h - (v - lo) / (hi - lo) * plot_h
    for t in ticks:
        svg.line(left, sy(t), left + plot_w, sy(t), "grid")
        svg.text(left - 8, sy(t), y_fmt(t), "tick", "end")
    for i, lab in (x_labels or []):
        svg.text(sx(i), h - bottom + 16, lab, "tick", "middle")
    for low, high, c in areas or []:
        pts = [f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(high)] + \
              [f"{sx(i):.1f},{sy(v):.1f}" for i, v in reversed(list(enumerate(low)))]
        svg.add(f'<polygon points="{" ".join(pts)}" class="a-{c}"/>')
    for lab, vals, c in series:
        pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
        svg.add(f'<polyline points="{pts}" class="l-{c}"/>')
        svg.add(f'<circle cx="{sx(len(vals) - 1):.1f}" cy="{sy(vals[-1]):.1f}" r="4" class="s-{c} dot-ring"/>')
        svg.text(sx(len(vals) - 1) + 8, sy(vals[-1]), y_fmt(vals[-1]), "val")
    # Hover columns: one per x, tooltip lists every series.
    colw = plot_w / (len(xs) - 1)
    for i, x in enumerate(xs):
        tip = f"{x}: " + "; ".join(f"{lab} {fmt_full(vals[i])} {unit}" for lab, vals, _ in series)
        svg.add(f'<g class="col"><line x1="{sx(i):.1f}" y1="{top}" x2="{sx(i):.1f}" y2="{top + plot_h}" class="hit-line"/>'
                f'<rect x="{sx(i) - colw / 2:.1f}" y="{top}" width="{colw:.1f}" height="{plot_h}" class="hit" '
                f'data-tip="{escape(tip)}"><title>{escape(tip)}</title></rect></g>')
    svg.line(left, top + plot_h, left + plot_w, top + plot_h, "axis")
    return svg.render()


def stacked_100(rows, parts, title, w=760, label_w=200, unit="wallets", total_fmt=None, total_label=None):
    """rows: [(label, total_count, [counts per part])]; parts: [(name, cls, text_cls)]."""
    bar, gap = 18, 14
    top = 40
    label_w = max(label_w, max(text_w(r[0]) for r in rows) + 20)
    h = top + len(rows) * (bar + gap) + 24
    svg = Svg(w, h, title)
    legend(svg, [(n, c) for n, c, _ in parts], label_w, 14)
    plot_w = w - label_w - 70
    y = top
    for label, total, counts in rows:
        svg.text(label_w - 10, y + bar / 2, label, "lab", "end")
        x = label_w
        tot = sum(counts) or 1
        for (name, cls, tcls), c in zip(parts, counts):
            seg = c / tot * plot_w
            if seg <= 0:
                continue
            share = c / tot * 100
            tip = (f"{label}: {name}, {share:.1f}% of the total" if "%" in unit
                   else f"{label}: {name}, {fmt_full(c)} {unit} ({share:.1f}%)")
            svg.rect(x, y, max(seg - 2, 0.5), bar, cls, tip)
            if seg > 36:
                svg.text(x + (seg - 2) / 2, y + bar / 2 + 0.5, f"{share:.0f}%", tcls, "middle")
            x += seg
        svg.text(label_w + plot_w + 8, y + bar / 2, total_fmt(total) if total_fmt else f"{total:,}", "val")
        y += bar + gap
    svg.text(label_w + plot_w + 8, top - 12, total_label or unit, "tick")
    return svg.render()


def diverging_bars(rows, title, w=760, label_w=230, unit="RBNT"):
    """rows: [(label, value)]. Positive values accent to the right, negative muted to the left."""
    bar, gap, top = 16, 12, 16
    label_w = max(label_w, max(text_w(r[0]) for r in rows) + 20)
    h = top + len(rows) * (bar + gap) + 30
    svg = Svg(w, h, title)
    vmax = max(abs(v) for _, v in rows) or 1
    plot_w = w - label_w - 40
    mid = label_w + plot_w / 2
    sx = lambda v: mid + v / vmax * (plot_w / 2 - 70)
    y = top
    for label, v in rows:
        svg.text(label_w - 10, y + bar / 2, label, "lab", "end")
        cls = ACCENT if v >= 0 else MUTED
        x0, x1 = sorted((mid, sx(v)))
        svg.rect(x0, y, x1 - x0, bar, cls, f"{label}: {'+' if v > 0 else ''}{fmt_full(v)} {unit}",
                 round_end="right" if v >= 0 else "left")
        svg.text(sx(v) + (6 if v >= 0 else -6), y + bar / 2, ("+" if v > 0 else "") + fmt_num(v), "val",
                 "start" if v >= 0 else "end")
        y += bar + gap
    svg.line(mid, top - 6, mid, h - 22, "axis")
    return svg.render()


def columns(cats, values, title, w=760, h=280, unit="RBNT", highlight=None, value_fmt=fmt_num):
    left, right, top, bottom = 56, 16, 20, 44
    svg = Svg(w, h, title)
    ticks = nice_ticks(0, max(values) or 1, 4)
    plot_h = h - top - bottom
    sy = lambda v: top + plot_h - v / ticks[-1] * plot_h
    for t in ticks:
        svg.line(left, sy(t), w - right, sy(t), "grid")
        svg.text(left - 8, sy(t), value_fmt(t, 0) if value_fmt is fmt_num else value_fmt(t), "tick", "end")
    band = (w - left - right) / len(cats)
    bw = min(24, band * 0.6)
    for i, (c, v) in enumerate(zip(cats, values)):
        cx = left + band * i + band / 2
        cls = ACCENT if highlight is None or i in highlight else MUTED
        svg.rect(cx - bw / 2, sy(v), bw, sy(0) - sy(v), cls, f"{c}: {fmt_full(v)} {unit}", round_end="top")
        if v and (len(cats) <= 14 or v == max(values)):
            svg.text(cx, sy(v) - 9, value_fmt(v), "val", "middle")
        for k, part in enumerate(wrap(c, 10)):
            svg.text(cx, h - bottom + 14 + k * 12, part, "tick", "middle")
    svg.line(left, sy(0), w - right, sy(0), "axis")
    return svg.render()


def lorenz_chart(points_start, points_end, title, w=520, h=420):
    left, right, top, bottom = 56, 24, 36, 48
    svg = Svg(w, h, title)
    legend(svg, [("30 Jun 2026", MUTED), ("30 Sep 2026", ACCENT)], left, 12)
    pw, ph = w - left - right, h - top - bottom
    sx = lambda x: left + x * pw
    sy = lambda y: top + ph - y / 100 * ph
    for t in (0, 25, 50, 75, 100):
        svg.line(left, sy(t), left + pw, sy(t), "grid")
        svg.text(left - 8, sy(t), f"{t}%", "tick", "end")
        svg.text(sx(t / 100), top + ph + 16, f"{t}%", "tick", "middle")
    svg.line(sx(0), sy(0), sx(1), sy(100), "l-ref")
    svg.text(sx(0.52), sy(55), "Equal holdings", "tick", "start")
    for pts, c in ((points_start, "muted"), (points_end, "accent")):
        d = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in pts)
        svg.add(f'<polyline points="{d}" class="l-{c}"/>')
    for (x, y0), (_, y1) in zip(points_start[::10], points_end[::10]):
        tip = f"Smallest {x * 100:.0f}% of wallets hold {y1:.2f}% of wallet RBNT (30 Jun: {y0:.2f}%)"
        svg.add(f'<g class="col"><line x1="{sx(x):.1f}" y1="{top}" x2="{sx(x):.1f}" y2="{top + ph}" class="hit-line"/>'
                f'<rect x="{sx(x) - pw / 40:.1f}" y="{top}" width="{pw / 20:.1f}" height="{ph}" class="hit" '
                f'data-tip="{escape(tip)}"><title>{escape(tip)}</title></rect></g>')
    svg.text(left + pw / 2, h - 10, "Share of wallets, smallest first", "lab", "middle")
    svg.line(left, top + ph, left + pw, top + ph, "axis")
    return svg.render()


def standalone(svg_markup, dark=False):
    """Wrap an SVG with its stylesheet so it renders on its own (PNG export, file download)."""
    vars_ = (":root{--c-grid:#223039;--c-axis:#34444f;--c-muted:#8fa1ad;--c-ink-dim:#c2ced6;--c-ink:#f1f5f8;"
             "--c-muted-mark:#8fa1ad;--c-light-mark:#34444f;--c-dark-mark:#c2ced6;--c-surface:#141f26}") if dark else ""
    style = f"<style>{vars_}{CSS}</style>"
    return svg_markup.replace("<title>", style + "<title>", 1)


def flow_diagram(flows, title, w=760, unit="RBNT"):
    """Two-column flow diagram. flows: [(source, target, amount)].

    Sources on the left, targets on the right, ribbon width in proportion to the
    amount. Ribbons are a muted wash; the node bars carry the accent.
    """
    left_nodes, right_nodes = [], []
    for s, t, _ in flows:
        if s not in left_nodes:
            left_nodes.append(s)
        if t not in right_nodes:
            right_nodes.append(t)
    out_tot = {n: sum(a for s, _, a in flows if s == n) for n in left_nodes}
    in_tot = {n: sum(a for _, t, a in flows if t == n) for n in right_nodes}
    total = sum(a for _, _, a in flows)
    node_gap, top, node_w, min_slot = 10, 16, 10, 30
    usable = 300
    scale = usable / total
    slot = lambda v: max(v * scale, min_slot)
    h_left = sum(slot(out_tot[n]) for n in left_nodes) + node_gap * (len(left_nodes) - 1)
    h_right = sum(slot(in_tot[n]) for n in right_nodes) + node_gap * (len(right_nodes) - 1)
    h = top + max(h_left, h_right) + 24
    svg = Svg(w, h, title)
    lx = max(text_w(n) for n in left_nodes) + 30
    rx = w - max(text_w(n) for n in right_nodes) - 30
    ly, ry = {}, {}
    y = top + (max(h_left, h_right) - h_left) / 2
    for n in left_nodes:
        hh = max(out_tot[n] * scale, 3)
        ly[n] = [y, y]
        svg.rect(lx - node_w, y, node_w, hh, ACCENT, f"{n} sent {fmt_full(out_tot[n])} {unit}")
        svg.text(lx - node_w - 8, y + 7, n, "lab", "end")
        svg.text(lx - node_w - 8, y + 21, fmt_num(out_tot[n]), "tick", "end")
        y += slot(out_tot[n]) + node_gap
    y = top + (max(h_left, h_right) - h_right) / 2
    for n in right_nodes:
        hh = max(in_tot[n] * scale, 3)
        ry[n] = [y, y]
        svg.rect(rx, y, node_w, hh, MUTED, f"{n} received {fmt_full(in_tot[n])} {unit}")
        svg.text(rx + node_w + 8, y + 7, n, "lab")
        svg.text(rx + node_w + 8, y + 21, fmt_num(in_tot[n]), "tick")
        y += slot(in_tot[n]) + node_gap
    for s, t, a in flows:
        th = max(a * scale, 1.5)
        y0, y1 = ly[s][1], ry[t][1]
        ly[s][1] += th
        ry[t][1] += th
        mx = (lx + rx) / 2
        d = (f"M{lx:.1f},{y0:.1f} C{mx:.1f},{y0:.1f} {mx:.1f},{y1:.1f} {rx:.1f},{y1:.1f} "
             f"L{rx:.1f},{y1 + th:.1f} C{mx:.1f},{y1 + th:.1f} {mx:.1f},{y0 + th:.1f} {lx:.1f},{y0 + th:.1f}Z")
        tip = f"{s} to {t}: {fmt_full(a)} {unit}"
        svg.add(f'<path d="{d}" class="a-muted ribbon" data-tip="{escape(tip)}" tabindex="0"><title>{escape(tip)}</title></path>')
    return svg.render()


def stacked_pair(rows, parts, title, w=760, label_w=200, unit="RBNT"):
    """Horizontal stacked bars in absolute units. rows: [(label, [values per part])]."""
    bar, gap, top = 18, 14, 40
    label_w = max(label_w, max(text_w(r[0]) for r in rows) + 20)
    h = top + len(rows) * (bar + gap) + 30
    svg = Svg(w, h, title)
    legend(svg, [(n, c) for n, c in parts], label_w, 14)
    vmax = max(sum(v) for _, v in rows) or 1
    ticks = nice_ticks(0, vmax, 4)
    plot_w = w - label_w - 80
    sx = lambda v: v / ticks[-1] * plot_w
    for t in ticks:
        svg.line(label_w + sx(t), top - 6, label_w + sx(t), h - 26, "grid")
        svg.text(label_w + sx(t), h - 14, fmt_num(t, 0), "tick", "middle")
    y = top
    for label, vals in rows:
        svg.text(label_w - 10, y + bar / 2, label, "lab", "end")
        x = label_w
        for (name, cls), v in zip(parts, vals):
            seg = sx(v)
            if seg > 0:
                svg.rect(x, y, max(seg - 2, 0.5), bar, cls, f"{label}: {name} {fmt_full(v)} {unit}")
            x += seg
        svg.text(x + 6, y + bar / 2, fmt_num(sum(vals)), "val")
        y += bar + gap
    return svg.render()
