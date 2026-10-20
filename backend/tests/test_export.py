from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("docx", reason="pip install -r requirements-dev.txt")
pytest.importorskip("pptx", reason="pip install -r requirements-dev.txt")

from training.export import parse_blocks, split_slides, write_docx, write_pptx  # noqa: E402

MARKDOWN = """# Title

> Generated note
> second line.

First paragraph that
continues here.

## Section

- one
  continued
- two

1. first
2. second

| Metric | Value |
|---|---|
| F1 | 0.8462 |

```
code line
```

![Confusion matrix](figures/missing.png)
"""


def test_blocks_are_recognised_in_order() -> None:
    kinds = [block[0] for block in parse_blocks(MARKDOWN)]
    assert kinds == ["heading", "quote", "paragraph", "heading", "bullets", "numbers", "table", "code", "image"]


def test_wrapped_lines_are_joined() -> None:
    blocks = parse_blocks(MARKDOWN)
    assert blocks[2] == ("paragraph", "First paragraph that continues here.")
    assert blocks[4] == ("bullets", ["one continued", "two"])
    assert blocks[1] == ("quote", "Generated note second line.")


def test_table_keeps_header_and_rows_without_the_separator() -> None:
    table = parse_blocks(MARKDOWN)[6]
    assert table == ("table", [["Metric", "Value"], ["F1", "0.8462"]])


def test_heading_levels_and_image_target() -> None:
    blocks = parse_blocks(MARKDOWN)
    assert blocks[0] == ("heading", (1, "Title"))
    assert blocks[3] == ("heading", (2, "Section"))
    assert blocks[8] == ("image", ("Confusion matrix", "figures/missing.png"))


def test_slides_are_split_and_front_matter_is_dropped() -> None:
    deck = "---\nmarp: true\npaginate: true\n---\n# One\n\ntext\n\n---\n\n## Two\n\n- a\n"
    slides = split_slides(deck)
    assert [title for title, _ in slides] == ["One", "Two"]
    assert slides[1][1] == [("bullets", ["a"])]


def test_docx_contains_the_text_the_table_and_survives_a_missing_image(tmp_path: Path) -> None:
    import docx

    target = tmp_path / "report.docx"
    write_docx([("Report", MARKDOWN, tmp_path)], target)
    document = docx.Document(str(target))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "First paragraph that continues here." in text
    assert "[Image not found: figures/missing.png]" in text
    assert document.tables[0].cell(1, 1).text == "0.8462"


def test_pptx_has_one_slide_per_section(tmp_path: Path) -> None:
    from pptx import Presentation

    deck = "---\nmarp: true\n---\n# One\n\ntext\n\n---\n\n## Two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    target = tmp_path / "deck.pptx"
    write_pptx(deck, target, tmp_path, pictures=[])
    presentation = Presentation(str(target))
    assert len(presentation.slides) == 2
    assert presentation.slides[1].shapes.title.text == "Two"
    assert any(shape.has_table for shape in presentation.slides[1].shapes)


def test_appendix_does_not_repeat_its_own_title(tmp_path: Path) -> None:
    import docx

    target = tmp_path / "report.docx"
    write_docx([("", "# Report\n\ntext\n", tmp_path), ("Appendix A: Results", "# Evaluation results\n\nbody\n", tmp_path)], target)
    headings = [p.text for p in docx.Document(str(target)).paragraphs if p.style.name.startswith(("Heading", "Title"))]
    assert headings == ["Report", "Appendix A: Results"]


def test_table_rows_are_not_split_across_pages(tmp_path: Path) -> None:
    import docx

    target = tmp_path / "report.docx"
    write_docx([("", MARKDOWN, tmp_path)], target)
    table = docx.Document(str(target)).tables[0]
    assert all(row._tr.xpath(".//w:cantSplit") for row in table.rows)


def test_screenshots_follow_the_system_slide(tmp_path: Path) -> None:
    from PIL import Image
    from pptx import Presentation

    picture = tmp_path / "shot.png"
    Image.new("RGB", (400, 300), "white").save(picture)
    deck = "---\nmarp: true\n---\n# Title\n\n---\n\n## System\n\n- a\n\n---\n\n## Results\n\n- b\n"
    target = tmp_path / "deck.pptx"
    write_pptx(deck, target, tmp_path, pictures=[("Application: analyzer", picture)])
    titles = [slide.shapes.title.text for slide in Presentation(str(target)).slides]
    assert titles == ["Title", "System", "Application: analyzer", "Results"]


def test_appendix_keeps_a_second_top_level_section(tmp_path: Path) -> None:
    """Third review: only the appendix's own title is dropped, not every level-1 heading."""
    import docx

    target = tmp_path / "report.docx"
    appendix = "# Evaluation results\n\nbody\n\n# Notes\n\nmore\n"
    write_docx([("", "# Report\n\ntext\n", tmp_path), ("Appendix A: Results", appendix, tmp_path)], target)
    headings = [p.text for p in docx.Document(str(target)).paragraphs if p.style.name.startswith(("Heading", "Title"))]
    assert headings == ["Report", "Appendix A: Results", "Notes"]
