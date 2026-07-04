"""Tests for PDF parsing and chunking.
"""

from app.models.types import Format, Authority, ChunkType
from app.ingestion.metadata import detect_formats, detect_authority, detect_gender
from app.ingestion.chunker import chunk_text
from app.ingestion.parser import PageText


class TestParser:
    """Test PDF text extraction."""
    
    def test_extract_text_placeholder(self):
        """Placeholder for PDF extraction test."""
        pass


class TestChunker:
    """Test law-number-aware chunking."""
    
    def test_chunk_detects_law_numbers(self):
        """Test that law number patterns are matched."""
        pages = [
            PageText(
                page_number=1,
                text="1.1 The players\nEach side shall consist of eleven players.",
                headings=[]
            )
        ]
        chunks = chunk_text(pages)
        assert len(chunks) == 1
        assert chunks[0].metadata.law_number == "1.1"
        assert chunks[0].metadata.parent_law == "1"
        assert chunks[0].metadata.chunk_type == ChunkType.CLAUSE

    def test_chunk_gender_metadata(self):
        """Test that gender is properly set in ChunkMetadata."""
        pages = [
            PageText(
                page_number=1,
                text="3.2 Women's matches\nSpecial rules for women.",
                headings=[]
            ),
            PageText(
                page_number=2,
                text="4.1 Men's matches\nSpecial rules for men.",
                headings=[]
            ),
            PageText(
                page_number=3,
                text="5.1 Standard match\nStandard rules.",
                headings=[]
            )
        ]
        chunks = chunk_text(pages)
        assert len(chunks) == 3
        # Match order should correspond to the parsed pages/sections
        # Note: chunk_text calls split_by_law_number, which parses laws.
        # Page 1 text: "3.2 Women's matches..." has law_number="3.2" (or "0" if it splits by LAW_NUMBER_PATTERN)
        # Wait, LAW_NUMBER_PATTERN is r'^(\d{1,2}(?:\.\d{1,2})*(?:\.\d{1,2})?)\s'
        # Since "3.2 Women's matches" starts with a law number followed by space, it is matched.
        # Let's assert on gender for the chunks:
        # We find the chunk with law_number "3.2"
        c32 = next(c for c in chunks if c.metadata.law_number == "3.2")
        c41 = next(c for c in chunks if c.metadata.law_number == "4.1")
        c51 = next(c for c in chunks if c.metadata.law_number == "5.1")
        
        assert c32.metadata.gender == "women"
        assert c41.metadata.gender == "men"
        assert c51.metadata.gender == "all"


class TestMetadata:
    """Test metadata extraction."""
    
    def test_detect_formats(self):
        """Test format detection from text."""
        assert Format.TEST in detect_formats("This applies to TEST matches.")
        assert Format.ODI in detect_formats("This applies to ONE-DAY matches.")
        assert Format.T20I in detect_formats("This applies to TWENTY20 matches.")
    
    def test_detect_authority(self):
        """Test ICC vs MCC detection."""
        assert detect_authority("Rules of the MCC Marylebone Cricket Club") == Authority.MCC
        assert detect_authority("ICC Standard Playing Conditions") == Authority.ICC

    def test_detect_gender(self):
        """Test gender detection from text."""
        assert detect_gender("This is for the Women's tournament.") == "women"
        assert detect_gender("Only Men are allowed.") == "men"
        assert detect_gender("Any cricket match can use this.") == "all"
        assert detect_gender("Both Men and Women can play.") == "all"
