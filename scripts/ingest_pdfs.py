"""One-shot PDF ingestion pipeline."""

from pathlib import Path
from app.ingestion.parser import extract_text
from app.ingestion.chunker import chunk_text
from app.ingestion.metadata import detect_formats, detect_authority, detect_year, detect_gender
from app.rag.embeddings import EmbeddingClient
from app.rag.vector_store import VectorStore


def ingest_pdfs(pdf_dir: str = "data/pdfs"):
    """Ingest all PDFs in the directory.
    
    Flow:
    1. Scan pdf_dir for PDF files
    2. Extract text per page
    3. Generate chunks with metadata
    4. Fetch embeddings in batch
    5. Clean old collections data
    6. Upsert to Qdrant
    """
    pdf_path = Path(pdf_dir)
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDFs found in {pdf_dir}")
        print("Place ICC/MCC law PDFs in data/pdfs/ and try again.")
        return
    
    print(f"Initializing EmbeddingClient and VectorStore...")
    embedding_client = EmbeddingClient()
    vector_store = VectorStore()
    
    total_chunks = 0
    
    for pdf_file in pdf_files:
        print(f"\nProcessing PDF: {pdf_file.name}")
        
        # 1. Parse text from PDF
        try:
            pages = extract_text(pdf_file)
            print(f"  Parsed {len(pages)} pages.")
        except Exception as e:
            print(f"  Error parsing {pdf_file.name}: {e}")
            continue
            
        if not pages:
            print(f"  No pages extracted from {pdf_file.name}. Skipping.")
            continue
            
        # Detect overall document authority and year from sample (e.g. first page)
        sample_text = pages[0].text if pages else ""
        try:
            authority = detect_authority(sample_text)
            year = detect_year(sample_text)
        except Exception as e:
            print(f"  Error detecting metadata: {e}")
            continue
        
        # Detect gender using metadata function (combining filename and cover text)
        gender = detect_gender(pdf_file.name + " " + sample_text)
            
        print(f"  Detected Authority: {authority.value}, Year: {year}, Gender: {gender}")
        
        # 2. Chunk text
        try:
            chunks = chunk_text(pages, default_authority=authority, default_year=year)
            print(f"  Generated {len(chunks)} chunks.")
        except Exception as e:
            print(f"  Error chunking text: {e}")
            continue
            
        if not chunks:
            continue
            
        # 3. Refine metadata for each chunk
        for chunk in chunks:
            chunk.metadata.gender = gender
            # Detect formatting and formats specific to this chunk
            try:
                chunk.metadata.formats = detect_formats(chunk.text)
            except Exception:
                pass
            
        # 4. Generate embeddings
        print(f"  Generating embeddings in batches...")
        try:
            texts = [c.text for c in chunks]
            embeddings = embedding_client.embed_batch(texts)
            for chunk, emb in zip(chunks, embeddings):
                chunk.embedding = emb
        except Exception as e:
            print(f"  Error generating embeddings: {e}")
            continue
            
        # 5. Clean up old records for this same authority and year to prevent duplicates
        print(f"  Cleaning up old records for {authority.value} ({year})...")
        try:
            vector_store.delete_by_year(authority=authority.value, year=year)
        except Exception as e:
            print(f"  Warning cleaning up old records: {e}")
            
        # 6. Upsert to vector store
        print(f"  Upserting chunks to Qdrant...")
        try:
            upserted_count = vector_store.upsert(chunks)
            print(f"  Successfully indexed {upserted_count} chunks in Qdrant.")
            total_chunks += upserted_count
        except Exception as e:
            print(f"  Error upserting chunks: {e}")
            continue
            
    print(f"\nIngestion complete. Total chunks indexed: {total_chunks}")


if __name__ == "__main__":
    ingest_pdfs()
