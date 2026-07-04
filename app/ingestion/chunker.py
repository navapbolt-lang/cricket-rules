"""Law-number-aware hierarchical chunking."""

import re
import uuid
from typing import Optional
from app.models.types import ChunkType, LawChunk, ChunkMetadata, Format, Authority
from app.ingestion.metadata import detect_gender


LAW_NUMBER_PATTERN = r'^(\d{1,2}(?:\.\d{1,2})*(?:\.\d{1,2})?)\s'


def chunk_text(pages_text: list, default_authority: Authority = Authority.ICC, default_year: int = 2025) -> list[LawChunk]:
    """Split extracted PDF text into law-numbered chunks.
    
    Args:
        pages_text: Output from parser.py (list of PageText)
        default_authority: Default authority (ICC or MCC)
        default_year: Default year of rules
        
    Returns:
        List of LawChunk objects with metadata
    """
    chunks = []
    chunk_index = 0

    for page in pages_text:
        law_sections = split_by_law_number(page.text)

        for section in law_sections:
            law_number = section["law_number"]
            text = section["text"].strip()
            if not text:
                continue

            parts = law_number.split(".")
            parent_law = parts[0] if len(parts) >= 1 else law_number

            if len(parts) == 1:
                chunk_type = ChunkType.SECTION
            elif len(parts) == 2:
                chunk_type = ChunkType.CLAUSE
            else:
                chunk_type = ChunkType.SUBCLAUSE

            title = extract_title(text, law_number)
            gender = detect_gender(text)

            meta = ChunkMetadata(
                law_number=law_number,
                parent_law=parent_law,
                title=title or f"Law {law_number}",
                formats=[Format.ALL],
                authority=default_authority,
                gender=gender,
                year=default_year,
                effective_date=f"{default_year}-04-01",
                page_number=page.page_number,
                chunk_index=chunk_index,
                chunk_type=chunk_type,
            )

            chunk = LawChunk(
                id=str(uuid.uuid4()),
                text=text,
                metadata=meta,
            )
            chunks.append(chunk)
            chunk_index += 1

    chunks = add_chunk_overlap(chunks, overlap_tokens=50)
    return chunks


def split_by_law_number(text: str) -> list[dict]:
    """Split text at law number boundaries.
    
    Returns list of {"law_number": str, "text": str} dicts.
    """
    lines = text.split("\n")
    sections = []
    current_law = "0"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                current_lines.append("")
            continue

        m = re.match(LAW_NUMBER_PATTERN, stripped)
        if m:
            if current_lines:
                sections.append({
                    "law_number": current_law,
                    "text": "\n".join(current_lines).strip(),
                })
            current_law = m.group(1)
            # Remove trailing dot if it exists in the law number match
            if current_law.endswith("."):
                current_law = current_law[:-1]
            rest = stripped[m.end():].strip()
            current_lines = [rest]
        else:
            current_lines.append(stripped)

    if current_lines:
        sections.append({
            "law_number": current_law,
            "text": "\n".join(current_lines).strip(),
        })

    return [s for s in sections if s["text"]]


def add_chunk_overlap(chunks: list[LawChunk], overlap_tokens: int = 50) -> list[LawChunk]:
    """Add token overlap between adjacent chunks."""
    if len(chunks) <= 1:
        return chunks

    for i in range(1, len(chunks)):
        prev_chunk = chunks[i - 1]
        prev_words = prev_chunk.text.split()
        if len(prev_words) > overlap_tokens:
            overlap_text = " ".join(prev_words[-overlap_tokens:])
            chunks[i].text = overlap_text + "\n" + chunks[i].text

    return chunks


def extract_title(text: str, law_number: str) -> str:
    """Extract a title for a law section. Looks for the first line or capital headers."""
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        m = re.match(r'^(\d+(?:\.\d+)*)\s+\.?\s*(.+?)$', stripped)
        if m and m.group(1) == law_number:
            return m.group(2).strip()
    for line in lines:
        if line.isupper() and len(line.strip()) > 3:
            return line.strip().title()
    return ""
