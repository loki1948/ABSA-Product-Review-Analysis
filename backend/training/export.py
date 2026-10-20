"""Turn the generated report and slides into submission files.

Run from the ``backend`` directory, after ``python -m training.report``:

    pip install -r requirements-dev.txt        # python-docx, python-pptx
    python -m training.export

Writes ``docs/submission/ABSA_Project_Report.docx`` (the report followed by the
full results, baseline, error-analysis and transfer documents as appendices)
and ``docs/submission/ABSA_Presentation.pptx``. The Markdown files stay the
source: change them (or rather the scripts that generate them) and export
again. A PDF of the report is made from the DOCX with Word, see
``docs/submission/README.md``.

Only the Markdown that this project's generators produce is supported:
headings, paragraphs, lists, tables, fenced code, block quotes and images.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Any

from app.paths import DOCS_DIR

logger = logging.getLogger("export")

Block = tuple[str, Any]
_IMAGE = re.compile(r"^!\[(.*?)\]\((.*?)\)$")
_NUMBERED = re.compile(r"^\d+\.\s+")
_INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`|\*[^*\s][^*]*?\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def parse_blocks(markdown: str) -> list[Block]:
    """Markdown text as a list of (kind, content) blocks, in document order."""
    blocks: list[Block] = []
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
        elif stripped.startswith("```"):
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(code)))
            i += 1
        elif stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            blocks.append(("heading", (level, stripped[level:].strip())))
            i += 1
        elif _IMAGE.match(stripped):
            alt, target = _IMAGE.match(stripped).groups()  # type: ignore[union-attr]
            blocks.append(("image", (alt, target)))
            i += 1
        elif stripped.startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(set(cell) <= set("-: ") for cell in cells):  # skip the |---| line
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows))
        elif stripped.startswith(">"):
            quote: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(("quote", " ".join(quote)))
        elif stripped.startswith("- ") or _NUMBERED.match(stripped):
            numbered = not stripped.startswith("- ")
            is_item = (lambda s: bool(_NUMBERED.match(s))) if numbered else (lambda s: s.startswith("- "))
            items: list[str] = []
            while i < len(lines) and lines[i].strip():
                current = lines[i].strip()
                if is_item(current):
                    items.append(_NUMBERED.sub("", current) if numbered else current[2:])
                elif lines[i].startswith(" ") and items:
                    items[-1] += " " + current  # wrapped line of the same item
                else:
                    break
                i += 1
            blocks.append(("numbers" if numbered else "bullets", items))
        else:
            paragraph: list[str] = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||>|```|- |!\[|\d+\.\s)", lines[i].strip()):
                paragraph.append(lines[i].strip())
                i += 1
            blocks.append(("paragraph", " ".join(paragraph)))
    return blocks


def split_slides(deck: str) -> list[tuple[str, list[Block]]]:
    """A Marp deck as (title, blocks) per slide; the front matter is dropped."""
    body = re.sub(r"\A---\n.*?\n---\n", "", deck, flags=re.DOTALL)
    slides: list[tuple[str, list[Block]]] = []
    for part in re.split(r"\n---\n", body):
        blocks = parse_blocks(part)
        if not blocks:
            continue
        title = blocks[0][1][1] if blocks[0][0] == "heading" else ""
        slides.append((title, blocks[1:] if title else blocks))
    return slides


def _plain(text: str) -> str:
    """Inline Markdown as plain text (for table cells and slides)."""
    text = _LINK.sub(r"\1", text)
    return re.sub(r"\*\*(.+?)\*\*|`(.+?)`|\*([^*\s][^*]*?)\*", lambda m: m.group(1) or m.group(2) or m.group(3), text)


def _add_runs(paragraph: Any, text: str) -> None:
    """Write ``text`` into a python-docx paragraph, honouring bold, italics and code."""
    from docx.shared import Pt

    for piece in _INLINE.split(_LINK.sub(r"\1", text)):
        if not piece:
            continue
        if piece.startswith("**"):
            paragraph.add_run(piece[2:-2]).bold = True
        elif piece.startswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name, run.font.size = "Consolas", Pt(9.5)
        elif piece.startswith("*"):
            paragraph.add_run(piece[1:-1]).italic = True
        else:
            paragraph.add_run(piece)


def _no_row_breaks(table: Any) -> None:
    """Stop Word from splitting a table row over two pages."""
    from docx.oxml import OxmlElement

    for row in table.rows:
        properties = row._tr.get_or_add_trPr()
        properties.append(OxmlElement("w:cantSplit"))


def _widen(table: Any, column: int, width: Any, total: Any) -> None:
    """Give ``column`` the stated width and share the rest among the other columns."""
    table.autofit = False
    others = (total - width) // max(1, len(table.columns) - 1)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            cell.width = width if index == column else others


def write_docx(parts: list[tuple[str, str, Path]], target: Path) -> None:
    """``parts`` is (appendix title or "", markdown, folder its images are relative to)."""
    import docx
    from docx.enum.text import WD_BREAK
    from docx.shared import Cm, Pt

    document = docx.Document()
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(11)
    for section in document.sections:
        section.left_margin = section.right_margin = Cm(2.5)
        section.top_margin = section.bottom_margin = Cm(2.5)

    for index, (title, markdown, base) in enumerate(parts):
        if index:
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        shift = 0
        title_skipped = False
        if index and title:
            document.add_heading(title, level=1)
            shift = 1  # the appendix's own headings move one level down
        for kind, content in parse_blocks(markdown):
            if kind == "heading":
                level, text = content
                if index and level == 1 and not title_skipped:
                    title_skipped = True
                    continue  # the appendix title already says it
                if index == 0 and level == 1:
                    document.add_heading(_plain(text), level=0)  # document title
                else:
                    document.add_heading(_plain(text), level=min(level + shift, 4))
            elif kind == "paragraph":
                _add_runs(document.add_paragraph(), content)
            elif kind == "quote":
                _add_runs(document.add_paragraph(style="Intense Quote"), content)
            elif kind in ("bullets", "numbers"):
                style = "List Bullet" if kind == "bullets" else "List Number"
                for n, item in enumerate(content):
                    paragraph = document.add_paragraph(style=style)
                    # A short list stays whole, so its last item is not stranded on a new page.
                    paragraph.paragraph_format.keep_with_next = len(content) <= 6 and n < len(content) - 1
                    _add_runs(paragraph, item)
            elif kind == "code":
                for code_line in content.split("\n"):
                    paragraph = document.add_paragraph()
                    paragraph.paragraph_format.space_after = Pt(0)
                    run = paragraph.add_run(code_line)
                    run.font.name, run.font.size = "Consolas", Pt(8.5)
            elif kind == "table" and content:
                # Keep the line that introduces the table, and all of its rows, on
                # one page: a table cut in two by a page break is hard to read.
                if document.paragraphs and len(content) <= 24:
                    document.paragraphs[-1].paragraph_format.keep_with_next = True
                table = document.add_table(rows=len(content), cols=len(content[0]))
                table.style = "Light Grid Accent 1"
                _no_row_breaks(table)
                wide = {"Sentence": 0, "Review": 1}.get(content[0][0] if content[0][0] == "Sentence" else content[0][1] if len(content[0]) > 1 else "")
                if wide is not None:
                    _widen(table, wide, Cm(7.5), Cm(16))
                for r, row in enumerate(content):
                    for c, cell in enumerate(row[: len(content[0])]):
                        table.cell(r, c).text = _plain(cell)
                        paragraph = table.cell(r, c).paragraphs[0]
                        paragraph.paragraph_format.keep_with_next = r < len(content) - 1 and len(content) <= 24
                        for run in paragraph.runs:
                            run.font.size = Pt(9)
                            run.bold = r == 0
                document.add_paragraph().paragraph_format.space_after = Pt(2)
            elif kind == "image":
                alt, relative = content
                path = base / relative
                if path.exists():
                    document.add_picture(str(path), width=Cm(13.5))
                    document.paragraphs[-1].paragraph_format.keep_with_next = True  # picture + caption
                    caption = document.add_paragraph(alt)
                    caption.runs[0].italic = True
                else:
                    document.add_paragraph(f"[Image not found: {relative}]")
    target.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(target))


def write_pptx(deck: str, target: Path, base: Path, pictures: list[tuple[str, Path]]) -> None:
    """One slide per deck section, then one slide per (title, image) in ``pictures``."""
    from pptx import Presentation
    from pptx.util import Inches, Pt

    presentation = Presentation()
    presentation.slide_width, presentation.slide_height = Inches(13.333), Inches(7.5)
    width = presentation.slide_width

    def titled(title: str) -> Any:
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])  # title only
        slide.shapes.title.text = title
        slide.shapes.title.left, slide.shapes.title.top = Inches(0.6), Inches(0.3)
        slide.shapes.title.width, slide.shapes.title.height = width - Inches(1.2), Inches(1.1)
        for paragraph in slide.shapes.title.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(32)
        return slide

    def add_pictures() -> None:
        for picture_title, path in pictures:
            if not path.exists():
                logger.warning("Screenshot not found, slide skipped: %s", path)
                continue
            slide = titled(picture_title)
            picture = slide.shapes.add_picture(str(path), Inches(0.6), Inches(1.45), height=Inches(5.8))
            if picture.width > width - Inches(1.2):  # very wide image: fit the width instead
                ratio = (width - Inches(1.2)) / picture.width
                picture.width, picture.height = int(picture.width * ratio), int(picture.height * ratio)
            picture.left = int((width - picture.width) / 2)

    pictures_added = False
    for number, (title, blocks) in enumerate(split_slides(deck)):
        if number == 0:
            slide = presentation.slides.add_slide(presentation.slide_layouts[0])
            slide.shapes.title.text = title
            slide.placeholders[1].text = "\n".join(_plain(c) for k, c in blocks if k == "paragraph")
            for paragraph in slide.shapes.title.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(34)
            continue
        slide = titled(title)
        top = Inches(1.5)
        for kind, content in blocks:
            if kind == "table" and content:
                rows, cols = len(content), len(content[0])
                height = Inches(0.55) * rows
                shape = slide.shapes.add_table(rows, cols, Inches(0.6), top, width - Inches(1.2), height)
                for r, row in enumerate(content):
                    for c, cell in enumerate(row[:cols]):
                        shape.table.cell(r, c).text = _plain(cell)
                        for paragraph in shape.table.cell(r, c).text_frame.paragraphs:
                            for run in paragraph.runs:
                                run.font.size = Pt(18)
                top += height + Inches(0.3)
                continue
            if kind == "image":
                path = base / content[1]
                if path.exists():
                    slide.shapes.add_picture(str(path), Inches(0.6), top, height=Inches(4.6))
                    top += Inches(4.8)
                continue
            lines = content if kind in ("bullets", "numbers") else content.split("\n") if kind == "code" else [content]
            box_height = Inches(0.55 if kind != "code" else 0.36) * len(lines) + Inches(0.15)
            box = slide.shapes.add_textbox(Inches(0.6), top, width - Inches(1.2), box_height)
            frame = box.text_frame
            frame.word_wrap = True
            for n, line in enumerate(lines):
                paragraph = frame.paragraphs[0] if n == 0 else frame.add_paragraph()
                prefix = "• " if kind == "bullets" else f"{n + 1}. " if kind == "numbers" else ""
                run = paragraph.add_run()
                run.text = prefix + (line if kind == "code" else _plain(line))
                run.font.size = Pt(16 if kind == "code" else 26)
                if kind == "code":
                    run.font.name = "Consolas"
                if kind == "quote":
                    run.font.italic = True
            top += box_height + Inches(0.15)
        if title == PICTURES_AFTER:
            add_pictures()
            pictures_added = True

    if not pictures_added:
        add_pictures()

    target.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(str(target))


# The screenshot slides are placed right after the slide with this title.
PICTURES_AFTER = "System"

APPENDICES = [
    ("Appendix A: Full evaluation results", "results.md"),
    ("Appendix B: Baseline comparison", "baseline.md"),
    ("Appendix C: Error analysis", "error_analysis.md"),
    ("Appendix D: Cross-domain transfer", "transfer.md"),
]
SCREENSHOT_SLIDES = [
    ("Application: analyzing one review", "screenshots/analyzer-result.png"),
    ("Application: batch analysis of a CSV file", "screenshots/batch-results.png"),
    ("Application: review history", "screenshots/history.png"),
    ("Application: dashboard and model performance", "screenshots/dashboard.png"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--docs", type=Path, default=DOCS_DIR)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    docs: Path = args.docs
    out = docs / "submission"
    parts = [("", (docs / "report.md").read_text(encoding="utf-8"), docs)]
    for title, name in APPENDICES:
        if (docs / name).exists():
            parts.append((title, (docs / name).read_text(encoding="utf-8"), docs))
        else:
            logger.warning("%s not found, appendix skipped", name)
    write_docx(parts, out / "ABSA_Project_Report.docx")
    write_pptx(
        (docs / "slides.md").read_text(encoding="utf-8"),
        out / "ABSA_Presentation.pptx",
        docs,
        [(title, docs / relative) for title, relative in SCREENSHOT_SLIDES],
    )
    logger.info("Written: %s", out)


if __name__ == "__main__":
    main()
