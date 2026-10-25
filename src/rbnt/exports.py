"""Exports of the report content: PNG charts, PDF, Word and the Excel workbook.

The report is written once as a list of content blocks (see scripts/09_build.py).
The HTML page, the Word file and the PDF are all rendered from that list, so the
three never say different things.
"""

import csv
import re
from html import unescape
from pathlib import Path

from . import config
from . import svgcharts as C

TAG = re.compile(r"<[^>]+>")


def plain(html):
    return unescape(TAG.sub("", html)).strip()


def launch(p):
    """Start Chromium. Uses CHROMIUM_PATH if set, else Playwright's own browser,
    else a system Chromium at /opt/pw-browsers/chromium."""
    import os
    path = os.environ.get("CHROMIUM_PATH")
    if path:
        return p.chromium.launch(executable_path=path)
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(executable_path="/opt/pw-browsers/chromium")


def charts_to_png(names, out_dir, scale=2):
    """Render each SVG chart on a white page with Chromium and save a PNG."""
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    fonts = (config.ROOT / "assets" / "fonts").as_uri()
    face = "".join(
        f'@font-face{{font-family:"Be Vietnam Pro";font-weight:{w};src:url("{fonts}/be-vietnam-pro-{w}.woff2")}}'
        for w in (400, 500, 600, 700)) + f'@font-face{{font-family:"JetBrains Mono";font-weight:400 600;src:url("{fonts}/jetbrains-mono.woff2")}}'
    with sync_playwright() as p:
        b = launch(p)
        page = b.new_page(device_scale_factor=scale)
        for name in names:
            svg = (config.ROOT / "report" / "charts" / f"{name}.svg").read_text()
            page.set_content(f"<html><head><style>{face}body{{margin:0;background:#fff}}{C.CSS}</style></head>"
                             f"<body><div id=c style='display:inline-block;padding:8px'>{svg}</div></body></html>")
            page.wait_for_timeout(150)
            page.locator("#c").screenshot(path=str(out_dir / f"{name}.png"))
        b.close()


def html_to_pdf(html_path, pdf_path, footer_text):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = launch(p)
        page = b.new_page()
        page.goto(Path(html_path).as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.evaluate("document.documentElement.setAttribute('data-theme','light')")
        page.wait_for_timeout(300)
        page.pdf(path=str(pdf_path), format="A4", print_background=True, display_header_footer=True,
                 header_template="<span></span>",
                 footer_template=(f'<div style="font-family:JetBrains Mono,monospace;font-size:7px;color:#596975;'
                                  f'width:100%;padding:0 13mm;display:flex;justify-content:space-between">'
                                  f'<span>{footer_text}</span><span>Page <span class="pageNumber"></span> of '
                                  f'<span class="totalPages"></span></span></div>'),
                 margin={"top": "14mm", "bottom": "16mm", "left": "13mm", "right": "13mm"})
        b.close()


def docx(blocks, path, png_dir, title, subtitle):
    """Word edition. Brand fonts are named so they apply where installed; the
    system sans is the fallback, never a serif."""
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    INK, DIM, RED, MUTED = RGBColor(0x0F, 0x1A, 0x22), RGBColor(0x39, 0x48, 0x53), RGBColor(0xB3, 0x27, 0x2A), RGBColor(0x59, 0x69, 0x75)
    d = Document()
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2)
        s.top_margin = s.bottom_margin = Cm(1.8)
    st = d.styles["Normal"]
    st.font.name = "Be Vietnam Pro"
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Be Vietnam Pro")
    st.font.size = Pt(10.5)
    st.font.color.rgb = DIM
    st.paragraph_format.line_spacing = 1.35
    st.paragraph_format.space_after = Pt(6)
    for name, size in (("Heading 1", 22), ("Heading 2", 16), ("Heading 3", 12.5)):
        h = d.styles[name]
        h.font.name = "Be Vietnam Pro"
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = INK

    def shade(cell, hex_):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), hex_)
        tcPr.append(shd)

    def add_rich(par, html):
        """Bold for <strong>/<b>, everything else plain."""
        for part in re.split(r"(<strong>.*?</strong>|<b>.*?</b>)", html):
            if not part:
                continue
            bold = part.startswith(("<strong>", "<b>"))
            run = par.add_run(unescape(TAG.sub("", part)))
            run.bold = bold
            if bold:
                run.font.color.rgb = INK

    def add_table(header, rows, numeric=None):
        numeric = numeric if numeric is not None else set(range(1, len(header)))
        t = d.add_table(rows=1, cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = "Table Grid"
        for i, h in enumerate(header):
            c = t.rows[0].cells[i]
            c.text = ""
            r = c.paragraphs[0].add_run(plain(str(h)))
            r.bold = True
            r.font.size = Pt(8)
            r.font.color.rgb = MUTED
            shade(c, "E6EBEF")
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                p = cells[i].paragraphs[0]
                r = p.add_run(plain(str(v)))
                r.font.size = Pt(8.5)
                if i in numeric:
                    r.font.name = "JetBrains Mono"
                    p.alignment = 2
        d.add_paragraph()

    p = d.add_paragraph()
    r = p.add_run("QUARTERLY ON-CHAIN HOLDER REPORT")
    r.bold = True
    r.font.size = Pt(9)
    r.font.color.rgb = RED
    d.add_heading(title, 1)
    d.add_paragraph(subtitle)
    logo = config.ROOT / "brand" / "logos" / "dao-logo-on-light.png"
    if logo.exists():
        d.add_picture(str(logo), height=Cm(2.2))

    for b in blocks:
        kind = b[0]
        if kind == "section":
            d.add_page_break()
            lab = d.add_paragraph()
            rr = lab.add_run(b[1].upper())
            rr.bold = True
            rr.font.size = Pt(8.5)
            rr.font.color.rgb = RED
            d.add_heading(b[2], 2)
        elif kind == "h3":
            d.add_heading(b[1], 3)
        elif kind in ("p", "answer"):
            par = d.add_paragraph()
            add_rich(par, b[1])
            if kind == "answer":
                for run in par.runs:
                    run.font.size = Pt(12)
                    run.font.color.rgb = INK
        elif kind == "list":
            for item in b[1]:
                add_rich(d.add_paragraph(style="List Bullet"), item)
        elif kind == "glance":
            for i, (head, body) in enumerate(b[1], 1):
                par = d.add_paragraph()
                r1 = par.add_run(f"{i:02d}  {plain(head)}. ")
                r1.bold = True
                r1.font.color.rgb = INK
                add_rich(par, body)
        elif kind in ("plain", "notice"):
            t = d.add_table(rows=1, cols=1)
            c = t.rows[0].cells[0]
            shade(c, "F4F6F8")
            c.text = ""
            if kind == "plain":
                lab = c.paragraphs[0].add_run(b[1].upper())
                lab.bold = True
                lab.font.size = Pt(8)
                lab.font.color.rgb = MUTED
                add_rich(c.add_paragraph(), b[2])
            else:
                first = True
                for para in b[1]:
                    add_rich(c.paragraphs[0] if first else c.add_paragraph(), para)
                    first = False
            d.add_paragraph()
        elif kind == "fig":
            _, num, title_, sub, chart, source, tbl = b
            lab = d.add_paragraph()
            rr = lab.add_run(f"FIGURE {num}")
            rr.bold = True
            rr.font.size = Pt(8)
            rr.font.color.rgb = MUTED
            h = d.add_paragraph()
            hr = h.add_run(title_)
            hr.bold = True
            hr.font.color.rgb = INK
            if sub:
                s = d.add_paragraph(plain(sub))
                s.runs[0].font.size = Pt(9)
            png = png_dir / f"{chart}.png"
            if png.exists():
                d.add_picture(str(png), width=Cm(16.5))
            src = d.add_paragraph(plain(source))
            src.runs[0].font.size = Pt(7.5)
            src.runs[0].font.color.rgb = MUTED
        elif kind == "table":
            add_table(b[1], b[2], b[3] if len(b) > 3 else None)
        elif kind == "check":
            par = d.add_paragraph()
            rr = par.add_run(b[1])
            rr.font.name = "JetBrains Mono"
            rr.font.size = Pt(7.5)
        elif kind == "gloss":
            for term, text in b[1]:
                par = d.add_paragraph()
                t1 = par.add_run(term + ". ")
                t1.bold = True
                t1.font.color.rgb = INK
                par.add_run(plain(text))
    d.core_properties.title = title
    d.core_properties.author = "Redbelly DAO"
    d.save(str(path))


def xlsx(path, files, about_rows):
    """One sheet per CSV, plus an About sheet with sources and definitions."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "About"
    for r in about_rows:
        ws.append(r)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 110
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    head_fill = PatternFill("solid", fgColor="E6EBEF")
    for name in files:
        p = config.data_dir("processed") / name
        sheet = wb.create_sheet(name.replace(".csv", "")[:31])
        with open(p) as f:
            for i, row in enumerate(csv.reader(f)):
                out = []
                for v in row:
                    try:
                        out.append(int(v) if re.fullmatch(r"-?\d+", v) else float(v) if re.fullmatch(r"-?\d+\.\d+", v) else v)
                    except ValueError:
                        out.append(v)
                sheet.append(out)
        for c in sheet[1]:
            c.font = Font(bold=True)
            c.fill = head_fill
        for col in sheet.columns:
            width = max(len(str(c.value or "")) for c in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max(12, width + 2), 48)
            for c in col[1:]:
                if isinstance(c.value, float):
                    c.number_format = "#,##0.00" if abs(c.value) >= 1000 else "0.0000"
                elif isinstance(c.value, int):
                    c.number_format = "#,##0"
        sheet.freeze_panes = "B2"
    wb.save(str(path))
