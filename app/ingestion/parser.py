"""PDF text extraction using PyMuPDF.

Extracts text from PDFs preserving page numbers and heading levels.
Handles multi-column layouts and detects headings by font size/weight.
Returns a list of PageText objects: {page_number: int, text: str, headings: list}
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional


class PageText:
    def __init__(self, page_number: int, text: str, headings: list[dict]):
        self.page_number = page_number
        self.text = text
        self.headings = headings


def extract_text(pdf_path: str | Path) -> list[PageText]:
    """ text from PDF, returning a list of PageText objects.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of PageText, one per page
        
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b["type"] == 0]

        lines = []
        headings = []
        for block in text_blocks:
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                span = spans[0]
                text = span.get("text", "").strip()
                if not text:
                    continue
                font_size = span.get("size", 12)
                is_bold = "Bold" in span.get("font", "")
                lines.append((font_size, is_bold, text))

        merged_lines = []
        i = 0
        while i < len(lines):
            if i < len(lines) - 1 and lines[i + 1][1] == lines[i][1] and abs(lines[i + 1][0] - lines[i][0]) < 0.5:
                merged_lines.append((lines[i][0], lines[i][1], lines[i][2] + " " + lines[i + 1][2]))
                i += 2
            else:
                merged_lines.append(lines[i])
                i += 1

        body_lines = []
        for font_size, is_bold, text in merged_lines:
            is_heading = font_size > 14 or (font_size > 12 and is_bold)
            if is_heading:
                headings.append({"text": text, "level": 1 if font_size > 16 else 2})
            body_lines.append(text)

        text = "\n".join(body_lines)
        pages.append(PageText(page_number=page_num + 1, text=text, headings=headings))

    doc.close()
    return pages


def get_headings_from_blocks(blocks: list[dict]) -> list[dict]:
    """Detect headings from text blocks based on font size and style."""
    headings = []
    for block in blocks:
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            span = spans[0]
            font_size = span.get("size", 12)
            is_bold = "Bold" in span.get("font", "")
            if font_size > 14 or (font_size > 12 and is_bold):
                headings.append({"text": span.get("text", "").strip(), "level": 1 if font_size > 16 else 2})
    return headings
