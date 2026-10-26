"""Hand-written SVG charts in the Task Board brand.

Each chart is plain SVG with CSS classes, so the same markup themes itself on
the web page (light and dark), prints into the PDF and renders to PNG for the
Word file. Marks carry a `data-tip` the page shows on hover or focus, and a
<title> for screen readers.

Colour: the red accent marks the value the chart is about (usually 30
September); slate marks the comparison. Labels and numbers stay in ink colours.
"""

from html import escape

STYLE = """
.viz{font-family:"Be Vietnam Pro",ui-sans-serif,system-ui,sans-serif;font-size:12px}
.viz .rule{stroke:var(--v-rule,#E6EBEF);stroke-width:1}
.viz .base{stroke:var(--v-base,#C3CDD4);stroke-width:1}
.viz .num{fill:var(--v-faint,#596975);font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px}
.viz .name{fill:var(--v-ink2,#394853)}
.viz .figure{fill:var(--v-ink,#0F1A22);font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px}
.viz .on-fill{fill:#fff;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px}
.viz .on-pale{fill:#0F1A22;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px}
.viz .red{fill:var(--v-red,#EF5350)}
.viz .slate{fill:var(--v-slate,#596975)}
.viz .mist{fill:var(--v-mist,#C3CDD4)}
.viz .ink{fill:var(--v-deep,#1d3140)}
.viz .pale{fill:var(--v-pale,#DAE1E7)}
.viz .stroke-red{stroke:var(--v-red,#EF5350);stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round}
.viz .stroke-slate{stroke:var(--v-slate,#596975);stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round}
.viz .stem{stroke:var(--v-base,#C3CDD4);stroke-width:3;stroke-linecap:round}
.viz .wash{fill:var(--v-red,#EF5350);opacity:.12}
.viz .ribbon{fill:var(--v-slate,#596975);opacity:.16}
.viz .ribbon:hover{opacity:.32}
.viz .ring{stroke:var(--v-surface,#fff);stroke-width:2}
.viz .hover{fill:transparent}
.viz .guide{stroke:var(--v-faint,#596975);stroke-width:1;opacity:0}
.viz g.slot:hover .guide{opacity:.55}
.viz [data-tip]:focus{outline:2px solid var(--v-red,#EF5350);outline-offset:1px}
"""

RED, SLATE, MIST, INK, PALE = "red", "slate", "mist", "ink", "pale"


def compact(v, places=1):
    """1.96B, 345.6M, 12.3K, 950 for axes and labels."""
    size, sign = abs(v), "-" if v < 0 else ""
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if size >= div * (10 if unit == "K" else 1):
            digits = 2 if unit == "B" else places
            text = f"{size / div:.{digits}f}"
            if places == 0:
                text = f"{size / div:g}"
            return f"{sign}{text}{unit}"
    return f"{sign}{size:,.0f}"


def whole(v):
    return f"{v:,.0f}"


def width_of(text, px=12):
    return len(str(text)) * px * 0.56


def tidy_steps(low, high, count=4):
    """Round axis steps that cover low..high."""
    span = (high - low) or 1
    raw = span / count
    power = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 10 ** -(len(str(int(1 / raw))))
    step = next(m * power for m in (1, 2, 2.5, 5, 10) if span / (m * power) <= count)
    first = (low // step) * step
    marks = []
    v = first
    while v < high + step * 0.999:
        marks.append(round(v, 10))
        v += step
    return marks


class Canvas:
    def __init__(self, w, h, title, desc=""):
        self.w, self.h, self.title, self.desc, self.out = w, h, title, desc, []

    def put(self, markup):
        self.out.append(markup)

    def label(self, x, y, text, cls="name", anchor="start"):
        self.put(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}" dominant-baseline="middle">'
                 f"{escape(str(text))}</text>")

    def line(self, x1, y1, x2, y2, cls):
        self.put(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}"/>')

    def box(self, x, y, w, h, cls, tip=None, cap=None):
        """A bar. cap rounds only the data end ('end' for horizontal, 'top' for vertical)."""
        w, h = max(w, 0), max(h, 0)
        extra = f' data-tip="{escape(tip)}" tabindex="0"' if tip else ""
        title = f"<title>{escape(tip)}</title>" if tip else ""
        if cap and w > 0 and h > 0:
            r = min(4, w / 2, h / 2)
            if cap == "end":
                d = f"M{x:.1f},{y:.1f}h{w - r:.1f}q{r},0 {r},{r}v{h - 2 * r:.1f}q0,{r} -{r},{r}h-{w - r:.1f}z"
            elif cap == "start":
                d = f"M{x + w:.1f},{y:.1f}h-{w - r:.1f}q-{r},0 -{r},{r}v{h - 2 * r:.1f}q0,{r} {r},{r}h{w - r:.1f}z"
            else:
                d = f"M{x:.1f},{y + h:.1f}v-{h - r:.1f}q0,-{r} {r},-{r}h{w - 2 * r:.1f}q{r},0 {r},{r}v{h - r:.1f}z"
            self.put(f'<path d="{d}" class="{cls}"{extra}>{title}</path>')
        else:
            self.put(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" class="{cls}"{extra}>{title}</rect>')

    def dot(self, x, y, cls, tip=None, r=5):
        extra = f' data-tip="{escape(tip)}" tabindex="0"' if tip else ""
        title = f"<title>{escape(tip)}</title>" if tip else ""
        self.put(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" class="{cls} ring"{extra}>{title}</circle>')

    def key(self, items, x, y):
        for text, cls, shape in items:
            if shape == "dot":
                self.dot(x + 5, y, cls, r=5)
            else:
                self.box(x, y - 5, 10, 10, cls)
            self.label(x + 16, y, text, "name")
            x += 16 + width_of(text) + 26

    def svg(self):
        return (f'<svg class="viz" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img" '
                f'aria-label="{escape(self.title)}" xmlns="http://www.w3.org/2000/svg"><title>{escape(self.title)}</title>'
                f"<desc>{escape(self.desc)}</desc>" + "".join(self.out) + "</svg>")


def strip(rows, parts, title, w=780, unit="RBNT", note=None):
    """100% horizontal strips, one per row. rows: [(row label, [value per part])]; parts: [(name, cls, text cls)].

    Segments are labelled inside when they fit; every segment has a tooltip.
    """
    lab_w = max(width_of(r[0]) for r in rows) + 18
    keys_per_line = max(1, int((w - 20) // 190))
    key_lines = (len(parts) + keys_per_line - 1) // keys_per_line
    top, bar, gap = 18 + key_lines * 22, 26, 16
    h = top + len(rows) * (bar + gap) + 8
    c = Canvas(w, h, title)
    for k in range(key_lines):
        c.key([(n, cls, "box") for n, cls, _ in parts[k * keys_per_line:(k + 1) * keys_per_line]], lab_w, 12 + k * 22)
    usable = w - lab_w - 8
    y = top
    for row_label, values in rows:
        c.label(lab_w - 10, y + bar / 2, row_label, "name", "end")
        whole_ = sum(values) or 1
        x = lab_w
        for (name, cls, text_cls), v in zip(parts, values):
            seg = v / whole_ * usable
            if seg <= 0:
                continue
            share = v / whole_ * 100
            c.box(x, y, max(seg - 2, 0.6), bar, cls,
                  f"{row_label}: {name}, {share:.1f}%" + (f" ({whole(v)} {unit})" if unit != "%" else ""))
            if seg > 44:
                c.label(x + (seg - 2) / 2, y + bar / 2 + 0.5, f"{share:.0f}%" if share >= 1 else f"{share:.1f}%", text_cls,
                        "middle")
            x += seg
        y += bar + gap
    return c.svg()


def dumbbell(rows, title, left_name, right_name, w=780, fmt=lambda v: f"{v:.1f}%", unit="%", tick=None):
    """One line per row joining two values: left (slate dot) and right (red dot).

    rows: [(row label, left value, right value)].
    """
    lab_w = max(width_of(r[0]) for r in rows) + 18
    top, step = 40, 34
    h = top + len(rows) * step + 30
    c = Canvas(w, h, title)
    c.key([(left_name, SLATE, "dot"), (right_name, RED, "dot")], lab_w, 14)
    high = max(max(a, b) for _, a, b in rows) or 1
    marks = tidy_steps(0, high, 4)
    span = w - lab_w - 70
    sx = lambda v: lab_w + v / marks[-1] * span
    for m in marks:
        c.line(sx(m), top - 8, sx(m), h - 26, "rule")
        c.label(sx(m), h - 12, (tick or fmt)(m), "num", "middle")
    y = top + step / 2 - 6
    for row_label, a, b in rows:
        c.label(lab_w - 10, y, row_label, "name", "end")
        c.line(sx(min(a, b)), y, sx(max(a, b)), y, "stem")
        c.dot(sx(a), y, SLATE, f"{row_label}, {left_name}: {fmt(a)}")
        c.dot(sx(b), y, RED, f"{row_label}, {right_name}: {fmt(b)}")
        c.label(sx(max(a, b)) + 10, y, f"{fmt(a)} / {fmt(b)}", "figure")
        y += step
    return c.svg()


def diverging(rows, title, w=780, unit="RBNT", fmt=None):
    """Signed values from a centre line: increases to the right in red, decreases to the left in slate."""
    fmt = fmt or (lambda v: ("+" if v > 0 else "") + compact(v))
    lab_w = max(width_of(r[0]) for r in rows) + 18
    bar, gap, top = 16, 12, 12
    h = top + len(rows) * (bar + gap) + 18
    c = Canvas(w, h, title)
    biggest = max(abs(v) for _, v in rows) or 1
    span = w - lab_w - 20
    centre = lab_w + span / 2
    sx = lambda v: centre + v / biggest * (span / 2 - 64)
    y = top
    for row_label, v in rows:
        c.label(lab_w - 10, y + bar / 2, row_label, "name", "end")
        a, b = sorted((centre, sx(v)))
        c.box(a, y, b - a, bar, RED if v >= 0 else SLATE,
              f"{row_label}: {('+' if v > 0 else '')}{whole(v)} {unit}", "end" if v >= 0 else "start")
        c.label(sx(v) + (7 if v >= 0 else -7), y + bar / 2, fmt(v), "figure", "start" if v >= 0 else "end")
        y += bar + gap
    c.line(centre, top - 6, centre, h - 8, "base")
    return c.svg()


def stacked(rows, parts, title, w=780, unit="RBNT"):
    """Horizontal stacked bars in real units. rows: [(label, [value per part])]."""
    lab_w = max(width_of(r[0]) for r in rows) + 18
    bar, gap, top = 18, 14, 40
    h = top + len(rows) * (bar + gap) + 30
    c = Canvas(w, h, title)
    c.key([(n, cls, "box") for n, cls in parts], lab_w, 14)
    marks = tidy_steps(0, max(sum(v) for _, v in rows) or 1, 4)
    span = w - lab_w - 80
    sx = lambda v: v / marks[-1] * span
    for m in marks:
        c.line(lab_w + sx(m), top - 6, lab_w + sx(m), h - 26, "rule")
        c.label(lab_w + sx(m), h - 12, compact(m, 0), "num", "middle")
    y = top
    for row_label, values in rows:
        c.label(lab_w - 10, y + bar / 2, row_label, "name", "end")
        x = lab_w
        for (name, cls), v in zip(parts, values):
            if v > 0:
                c.box(x, y, max(sx(v) - 2, 0.6), bar, cls, f"{row_label}: {name} {whole(v)} {unit}")
            x += sx(v)
        c.label(x + 6, y + bar / 2, compact(sum(values)), "figure")
        y += bar + gap
    return c.svg()


def columns(names, values, title, w=780, h=270, unit="RBNT"):
    left, right, top, bottom = 56, 14, 22, 44
    c = Canvas(w, h, title)
    marks = tidy_steps(0, max(values) or 1, 4)
    plot = h - top - bottom
    sy = lambda v: top + plot - v / marks[-1] * plot
    for m in marks:
        c.line(left, sy(m), w - right, sy(m), "rule")
        c.label(left - 8, sy(m), compact(m, 0), "num", "end")
    lane = (w - left - right) / len(names)
    bw = min(22, lane * 0.55)
    for k, (n, v) in enumerate(zip(names, values)):
        cx = left + lane * (k + 0.5)
        c.box(cx - bw / 2, sy(v), bw, sy(0) - sy(v), RED, f"{n}: {whole(v)} {unit}", "top")
        c.label(cx, sy(v) - 9, compact(v), "figure", "middle")
        c.label(cx, h - bottom + 15, n, "num", "middle")
    c.line(left, sy(0), w - right, sy(0), "base")
    return c.svg()


def daily(days, series, title, w=780, h=280, unit="RBNT", shade_between=None, ticks=None):
    """Lines over the days of the quarter. series: [(name, values, 'red'|'slate')].

    shade_between=(i, j) washes the gap between two series.
    """
    left, right, top, bottom = 62, 110, 38, 34
    c = Canvas(w, h, title)
    c.key([(n, RED if col == "red" else SLATE, "box") for n, _, col in series], left, 13)
    every = [v for _, vals, _ in series for v in vals]
    marks = tidy_steps(min(every), max(every), 4)
    low, high = marks[0], marks[-1]
    pw, ph = w - left - right, h - top - bottom
    sx = lambda k: left + k / (len(days) - 1) * pw
    sy = lambda v: top + ph - (v - low) / (high - low) * ph
    for m in marks:
        c.line(left, sy(m), left + pw, sy(m), "rule")
        c.label(left - 8, sy(m), compact(m, 1), "num", "end")
    for k, text in ticks or []:
        c.label(sx(k), h - bottom + 16, text, "num", "middle")
    if shade_between:
        a, b = series[shade_between[0]][1], series[shade_between[1]][1]
        pts = [f"{sx(k):.1f},{sy(v):.1f}" for k, v in enumerate(a)] + \
              [f"{sx(k):.1f},{sy(v):.1f}" for k, v in reversed(list(enumerate(b)))]
        c.put(f'<polygon points="{" ".join(pts)}" class="wash"/>')
    for name, vals, col in series:
        c.put(f'<polyline points="{" ".join(f"{sx(k):.1f},{sy(v):.1f}" for k, v in enumerate(vals))}" '
              f'class="stroke-{col}"/>')
        c.dot(sx(len(vals) - 1), sy(vals[-1]), col, r=4)
        c.label(sx(len(vals) - 1) + 9, sy(vals[-1]), compact(vals[-1]), "figure")
    lane = pw / (len(days) - 1)
    for k, day in enumerate(days):
        tip = f"{day}: " + "; ".join(f"{n} {whole(vals[k])} {unit}" for n, vals, _ in series)
        c.put(f'<g class="slot"><line x1="{sx(k):.1f}" y1="{top}" x2="{sx(k):.1f}" y2="{top + ph}" class="guide"/>'
              f'<rect x="{sx(k) - lane / 2:.1f}" y="{top}" width="{lane:.1f}" height="{ph}" class="hover" '
              f'data-tip="{escape(tip)}"><title>{escape(tip)}</title></rect></g>')
    c.line(left, top + ph, left + pw, top + ph, "base")
    return c.svg()


def flows(links, title, w=780, unit="RBNT"):
    """Senders on the left, receivers on the right, ribbon width in proportion to the amount.

    links: [(sender, receiver, amount)].
    """
    senders, receivers = [], []
    for s, r, _ in links:
        senders += [s] if s not in senders else []
        receivers += [r] if r not in receivers else []
    out_total = {s: sum(a for x, _, a in links if x == s) for s in senders}
    in_total = {r: sum(a for _, x, a in links if x == r) for r in receivers}
    scale = 300 / sum(a for _, _, a in links)
    room = lambda v: max(v * scale, 30)
    gap, top, node = 10, 14, 10
    hl = sum(room(out_total[s]) for s in senders) + gap * (len(senders) - 1)
    hr = sum(room(in_total[r]) for r in receivers) + gap * (len(receivers) - 1)
    h = top + max(hl, hr) + 20
    c = Canvas(w, h, title)
    lx = max(width_of(s) for s in senders) + 30
    rx = w - max(width_of(r) for r in receivers) - 30
    y_out, y_in = {}, {}
    y = top + (max(hl, hr) - hl) / 2
    for s in senders:
        c.box(lx - node, y, node, max(out_total[s] * scale, 3), RED, f"{s} sent {whole(out_total[s])} {unit}")
        c.label(lx - node - 8, y + 7, s, "name", "end")
        c.label(lx - node - 8, y + 21, compact(out_total[s]), "num", "end")
        y_out[s] = y
        y += room(out_total[s]) + gap
    y = top + (max(hl, hr) - hr) / 2
    for r in receivers:
        c.box(rx, y, node, max(in_total[r] * scale, 3), SLATE, f"{r} received {whole(in_total[r])} {unit}")
        c.label(rx + node + 8, y + 7, r, "name")
        c.label(rx + node + 8, y + 21, compact(in_total[r]), "num")
        y_in[r] = y
        y += room(in_total[r]) + gap
    mid = (lx + rx) / 2
    for s, r, a in links:
        t = max(a * scale, 1.5)
        y0, y1 = y_out[s], y_in[r]
        y_out[s] += t
        y_in[r] += t
        d = (f"M{lx:.1f},{y0:.1f} C{mid:.1f},{y0:.1f} {mid:.1f},{y1:.1f} {rx:.1f},{y1:.1f} V{y1 + t:.1f} "
             f"C{mid:.1f},{y1 + t:.1f} {mid:.1f},{y0 + t:.1f} {lx:.1f},{y0 + t:.1f}Z")
        tip = f"{s} to {r}: {whole(a)} {unit}"
        c.put(f'<path d="{d}" class="ribbon" data-tip="{escape(tip)}" tabindex="0"><title>{escape(tip)}</title></path>')
    return c.svg()


def standalone(markup):
    """Embed the stylesheet so an SVG renders on its own (PNG export)."""
    return markup.replace("<title>", f"<style>{STYLE}</style><title>", 1)
