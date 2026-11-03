import io

import pytest
from docx import Document
from pypdf import PdfWriter
from pypdf.errors import PdfReadError

from app.utils.pdf_parser import extract_text_from_pdf
from app.utils.text_extraction import (
    extract_text,
    extract_text_from_docx,
    extract_text_from_txt,
)


def _make_pdf(text: str) -> bytes:
    """Build a tiny valid one-page PDF containing `text` (no extra libraries)."""
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        (
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 200]/Contents 4 0 R"
            b"/Resources<</Font<</F1 5 0 R>>>>>>"
        ),
        b"<</Length "
        + str(len(stream)).encode()
        + b">>\nstream\n"
        + stream
        + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica/Encoding/WinAnsiEncoding>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<</Size {len(objects) + 1}/Root 1 0 R>>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


def _make_docx(paragraphs, table_cells=None) -> bytes:
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    if table_cells:
        table = doc.add_table(rows=1, cols=len(table_cells))
        for cell, text in zip(table.rows[0].cells, table_cells, strict=True):
            cell.text = text
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# ------------------------------------------------------------------ txt


def test_txt_is_decoded_as_utf8():
    assert extract_text_from_txt("Résumé of Asha".encode()) == "Résumé of Asha"


def test_txt_ignores_undecodable_bytes():
    assert extract_text_from_txt(b"Hello \xff World") == "Hello  World"


# ----------------------------------------------------------------- docx


def test_docx_paragraphs_are_joined_and_blank_ones_skipped():
    data = _make_docx(["Line one", "   ", "Line two"])
    assert extract_text_from_docx(data) == "Line one\nLine two"


def test_docx_table_cells_are_included_after_paragraphs():
    data = _make_docx(["Skills"], table_cells=["Python", "SQL"])
    assert extract_text_from_docx(data).splitlines() == ["Skills", "Python", "SQL"]


def test_docx_empty_table_cells_are_skipped():
    data = _make_docx(["Header"], table_cells=["Python", ""])
    assert extract_text_from_docx(data).splitlines() == ["Header", "Python"]


# ------------------------------------------------------------------ pdf


def test_pdf_text_is_extracted():
    text = extract_text_from_pdf(_make_pdf("Hello Resume Python"))
    assert "Hello Resume Python" in text


def test_pdf_without_text_returns_empty_string():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)

    assert extract_text_from_pdf(buffer.getvalue()) == ""


def test_invalid_pdf_raises():
    with pytest.raises(PdfReadError):
        extract_text_from_pdf(b"this is not a pdf")


# ------------------------------------------------------------- dispatch


def test_dispatch_by_extension():
    assert extract_text("cv.txt", b"plain text") == "plain text"
    assert "Hello Resume" in extract_text("cv.pdf", _make_pdf("Hello Resume"))
    assert extract_text("cv.docx", _make_docx(["From Word"])) == "From Word"


def test_extension_is_case_insensitive():
    assert extract_text("CV.TXT", b"upper") == "upper"
    assert "Hello" in extract_text("CV.PDF", _make_pdf("Hello"))


def test_only_the_last_extension_counts():
    assert extract_text("my.cv.final.txt", b"dots") == "dots"


@pytest.mark.parametrize("filename", ["photo.png", "notes.md", "resume", "archive."])
def test_unsupported_types_are_rejected(filename):
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(filename, b"data")


def test_error_message_lists_supported_types():
    with pytest.raises(ValueError, match="docx, pdf, txt"):
        extract_text("photo.png", b"data")
