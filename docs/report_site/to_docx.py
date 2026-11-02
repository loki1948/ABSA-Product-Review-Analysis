"""Write the report as a Word document from docs/report_site/index.html.

Run after build.py:   python docs/report_site/to_docx.py
Output: docs/submission/ABSA_Project_Report_Template.docx
Open it in Word and update the table of contents once (right-click it, Update Field),
or run update_toc.ps1 to have Word do that.
"""
from pathlib import Path

import docx
from bs4 import BeautifulSoup, NavigableString, Tag
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "submission" / "ABSA_Project_Report_Template.docx"
FONT = "Times New Roman"
COLORS = {"pass": RGBColor(0x1E, 0x7A, 0x46), "fail": RGBColor(0xB3, 0x26, 0x1E), "part": RGBColor(0x8A, 0x5A, 0x00)}
TEXT_WIDTH = Cm(15.5)


def set_font(style, size, bold=None, italic=None):
    style.font.name = FONT
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), FONT)
    for theme in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(theme), None)


def field(paragraph, instruction, placeholder=""):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, sep, text, end):
        run._r.append(element)


class Writer:
    def __init__(self):
        self.doc = docx.Document()
        set_font(self.doc.styles["Normal"], 12)
        self.doc.styles["Normal"].paragraph_format.space_after = Pt(6)
        self.doc.styles["Normal"].paragraph_format.line_spacing = 1.15
        set_font(self.doc.styles["Title"], 20, bold=True)
        set_font(self.doc.styles["Heading 1"], 14, bold=True)
        set_font(self.doc.styles["Heading 2"], 12, bold=True)
        set_font(self.doc.styles["Heading 3"], 12, bold=True, italic=True)
        for name in ("Heading 1", "Heading 2", "Heading 3"):
            self.doc.styles[name].paragraph_format.space_before = Pt(12)
            self.doc.styles[name].paragraph_format.space_after = Pt(6)
        section = self.doc.sections[0]
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        section.left_margin, section.right_margin = Cm(3), Cm(2.5)
        section.top_margin = section.bottom_margin = Cm(2.5)
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        field(footer, "PAGE", "1")

    # ---- inline content -------------------------------------------------
    def runs(self, paragraph, node, fmt=None):
        fmt = dict(fmt or {})
        if isinstance(node, NavigableString):
            text = str(node).replace("\n", " ")
            if not text:
                return
            while "  " in text:
                text = text.replace("  ", " ")
            run = paragraph.add_run(text)
            run.bold = fmt.get("bold")
            run.italic = fmt.get("italic")
            if fmt.get("code"):
                run.font.name = "Consolas"
                run.font.size = Pt(10)
            if fmt.get("size"):
                run.font.size = fmt["size"]
            if fmt.get("sub"):
                run.font.subscript = True
            if fmt.get("sup"):
                run.font.superscript = True
            if fmt.get("fill"):
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            if fmt.get("color"):
                run.font.color.rgb = fmt["color"]
            return
        if not isinstance(node, Tag):
            return
        name, classes = node.name, node.get("class") or []
        if name in ("b", "strong", "th"):
            fmt["bold"] = True
        if name in ("i", "em"):
            fmt["italic"] = True
        if name == "code":
            fmt["code"] = True
        if name == "sub":
            fmt["sub"] = True
        if name == "sup":
            fmt["sup"] = True
        if name == "br":
            paragraph.add_run().add_break()
            return
        if "fill" in classes:
            fmt["fill"] = True
        for key in ("pass", "fail", "part"):
            if key in classes:
                fmt["color"], fmt["bold"] = COLORS[key], True
        if "no" in classes:
            paragraph.add_run("\t")
        for child in node.children:
            self.runs(paragraph, child, fmt)

    def paragraph(self, node, align=WD_ALIGN_PARAGRAPH.JUSTIFY, style=None, fmt=None):
        p = self.doc.add_paragraph(style=style)
        p.alignment = align
        self.runs(p, node, fmt)
        # trim leading/trailing spaces
        if p.runs:
            p.runs[0].text = p.runs[0].text.lstrip()
            p.runs[-1].text = p.runs[-1].text.rstrip()
        return p

    # ---- blocks ---------------------------------------------------------
    def caption(self, text_node, above):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6 if above else 2)
        p.paragraph_format.keep_with_next = above
        self.runs(p, text_node, {"size": Pt(10), "bold": above or None})
        return p

    def table(self, node):
        cap = node.find("caption")
        if cap:
            self.caption(cap, above=True)
        rows = node.find_all("tr")
        ncols = max(sum(int(c.get("colspan", 1)) for c in r.find_all(["th", "td"])) for r in rows)
        table = self.doc.add_table(rows=len(rows), cols=ncols)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        size = Pt(9) if ncols >= 5 else Pt(10)
        for r, row in enumerate(rows):
            tr_pr = table.rows[r]._tr.get_or_add_trPr()
            tr_pr.append(OxmlElement("w:cantSplit"))
            if r == 0:
                header = OxmlElement("w:tblHeader")
                tr_pr.append(header)
            c = 0
            highlight = "hl" in (row.get("class") or [])
            for cell_node in row.find_all(["th", "td"]):
                span = int(cell_node.get("colspan", 1))
                cell = table.cell(r, c)
                if span > 1:
                    cell = cell.merge(table.cell(r, c + span - 1))
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                if "n" in (cell_node.get("class") or []):
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                self.runs(p, cell_node, {"size": size, "bold": (cell_node.name == "th" or highlight) or None})
                if cell_node.name == "th" or highlight:
                    shading = OxmlElement("w:shd")
                    shading.set(qn("w:val"), "clear")
                    shading.set(qn("w:fill"), "D9E2F3" if cell_node.name == "th" else "EEF3FA")
                    cell._tc.get_or_add_tcPr().append(shading)
                c += span
        if len(rows) <= 22:
            for row in table.rows[:-1]:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.keep_with_next = True
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)

    def figure(self, node):
        img = node.find("img")
        path = HERE / img["src"]
        width = Cm(6.5) if "phone" in path.name else Cm(11) if "confusion" in path.name else TEXT_WIDTH
        self.doc.add_picture(str(path), width=width)
        pic = self.doc.paragraphs[-1]
        pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic.paragraph_format.keep_with_next = True
        self.caption(node.find("figcaption"), above=False)

    def pre(self, node):
        lines = node.get_text().split("\n")
        for i, line in enumerate(lines):
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.left_indent = Cm(0.5)
            p.paragraph_format.keep_with_next = i < len(lines) - 1
            run = p.add_run(line if line else " ")
            run.font.name = "Consolas"
            run.font.size = Pt(8.5)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def list_(self, node):
        classes = node.get("class") or []
        if "refs" in classes:
            for li in node.find_all("li", recursive=False):
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(1.0)
                p.paragraph_format.first_line_indent = Cm(-1.0)
                p.paragraph_format.space_after = Pt(4)
                spans = li.find_all("span", recursive=False)
                p.add_run(spans[0].get_text() + "\t")
                self.runs(p, spans[1], {"size": Pt(11)})
            return
        if "check" in classes:
            for li in node.find_all("li", recursive=False):
                spans = li.find_all("span", recursive=False)
                p = self.doc.add_paragraph()
                p.paragraph_format.space_after = Pt(2)
                p.add_run(spans[0].get_text() + "  ").bold = True
                self.runs(p, spans[1])
            return
        style = "List Number" if node.name == "ol" else "List Bullet"
        for li in node.find_all("li", recursive=False):
            p = self.paragraph(li, align=WD_ALIGN_PARAGRAPH.LEFT, style=style)
            p.paragraph_format.space_after = Pt(3)

    def block(self, node):
        if isinstance(node, NavigableString) or not isinstance(node, Tag):
            return
        name, classes = node.name, node.get("class") or []
        if name in ("div", "section", "main") and "table-wrap" not in classes:
            for child in node.children:
                self.block(child)
        elif "table-wrap" in classes:
            self.table(node.find("table"))
        elif name == "h2":
            num = node.find("span", class_="num")
            label = num.get_text() if num else ""
            if num:
                num.extract()
            title = node.get_text().strip()
            heading = self.doc.add_heading(f"{label}. {title}" if label and label != "✓" else title, level=1)
            heading.paragraph_format.page_break_before = True
        elif name == "h3":
            self.doc.add_heading(node.get_text().strip(), level=2).paragraph_format.keep_with_next = True
        elif name == "h4":
            self.doc.add_heading(node.get_text().strip(), level=3).paragraph_format.keep_with_next = True
        elif name == "p":
            if "eq" in classes:
                p = self.paragraph(node, align=WD_ALIGN_PARAGRAPH.CENTER, fmt={"italic": True})
                p.paragraph_format.tab_stops.add_tab_stop(TEXT_WIDTH)
            elif "listing" in classes:
                p = self.paragraph(node, align=WD_ALIGN_PARAGRAPH.LEFT, fmt={"italic": True, "size": Pt(10)})
                p.paragraph_format.keep_with_next = True
            elif "keywords" in classes:
                self.paragraph(node, align=WD_ALIGN_PARAGRAPH.LEFT)
            else:
                self.paragraph(node)
        elif name in ("ol", "ul"):
            self.list_(node)
        elif name == "figure":
            self.figure(node)
        elif name == "pre":
            self.pre(node)
        elif name == "table":
            self.table(node)

    def cover(self, header):
        for _ in range(5):
            self.doc.add_paragraph()
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(header.find("h1").get_text().strip())
        run.bold, run.font.size = True, Pt(20)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(36)
        p.add_run("Project Report").font.size = Pt(14)
        for dt, dd in zip(header.find_all("dt"), header.find_all("dd")):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(dt.get_text() + ": ").bold = True
            self.runs(p, dd)
        # Contents page
        heading = self.doc.add_paragraph()
        heading.paragraph_format.page_break_before = True
        run = heading.add_run("Contents")
        run.bold, run.font.size = True, Pt(14)
        field(self.doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u',
              "Right-click here and choose Update Field to show the table of contents.")

    def build(self):
        soup = BeautifulSoup((HERE / "index.html").read_text(encoding="utf-8"), "html.parser")
        main = soup.find("main")
        self.cover(main.find("header", class_="cover"))
        for section in main.find_all("section", recursive=False):
            self.block(section)
        # Word asks to update fields when the document opens, so the contents fill in.
        settings = self.doc.settings.element
        update = OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        settings.append(update)
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(TARGET))
        print("written", TARGET)


if __name__ == "__main__":
    Writer().build()
