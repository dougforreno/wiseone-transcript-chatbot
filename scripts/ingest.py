#!/usr/bin/env python3
"""
Ingest transcript markdown files into Supabase with vector embeddings.

Usage:
    python scripts/ingest.py /path/to/transcripts/
    python scripts/ingest.py /path/to/transcripts/ --dry-run
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import date

import tiktoken
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
BATCH_SIZE = 20  # embeddings per API call

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")


# --- Parsing ---

def parse_transcript(filepath: Path) -> dict:
    """Parse a transcript markdown file into structured data."""
    text = filepath.read_text(encoding="utf-8")
    filename = filepath.name

    # Extract date from filename
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
    session_date = date_match.group(1) if date_match else None

    # Extract title (first H1)
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else filename.replace(".md", "")

    # Extract participants
    participants = []
    part_match = re.search(r"##\s*Participants?\s*\n([\s\S]*?)(?=\n##|\Z)", text)
    if part_match:
        for line in part_match.group(1).strip().split("\n"):
            line = line.strip().lstrip("- *")
            if line:
                name = re.split(r"\s*[\(\[]", line)[0].strip()
                if name:
                    participants.append(name)

    # Extract themes from bold Key themes line or Topic line
    themes = []
    theme_match = re.search(r"\*\*Key themes?:?\*\*\s*(.+)", text)
    if theme_match:
        themes = [t.strip() for t in theme_match.group(1).split(",")]
    else:
        topic_match = re.search(r"\*\*Topic:?\*\*\s*(.+)", text)
        if topic_match:
            themes = [t.strip() for t in topic_match.group(1).split(",")]

    # Extract duration
    duration = None
    dur_match = re.search(r"\*\*Duration:?\*\*\s*(.+)", text)
    if dur_match:
        duration = dur_match.group(1).strip()

    return {
        "filename": filename,
        "session_date": session_date,
        "title": title,
        "themes": themes,
        "participants": participants,
        "duration": duration,
        "raw_content": text,
    }


# --- Chunking ---

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping chunks, preserving section headers."""
    chunks = []
    current_section = None

    # Split into sections by H2/H3 headers
    sections = re.split(r"(?=^#{2,3}\s+)", text, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue

        # Check if section starts with a header
        header_match = re.match(r"^(#{2,3}\s+.+)$", section, re.MULTILINE)
        if header_match:
            current_section = header_match.group(1).strip().lstrip("#").strip()

        # Tokenize and chunk
        tokens = tokenizer.encode(section)
        if len(tokens) <= chunk_size:
            chunks.append({
                "content": section.strip(),
                "section_header": current_section,
                "token_count": len(tokens),
            })
        else:
            # Split into overlapping token windows
            start = 0
            while start < len(tokens):
                end = min(start + chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text_decoded = tokenizer.decode(chunk_tokens)
                chunks.append({
                    "content": chunk_text_decoded.strip(),
                    "section_header": current_section,
                    "token_count": len(chunk_tokens),
                })
                if end >= len(tokens):
                    break
                start += chunk_size - overlap

    return chunks


# --- Embeddings ---

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


# --- Ingestion ---

def ingest_transcript(filepath: Path, dry_run: bool = False) -> dict:
    """Ingest a single transcript file."""
    print(f"\n📄 Processing: {filepath.name}")

    # Parse
    doc = parse_transcript(filepath)
    print(f"   Title: {doc['title']}")
    print(f"   Date: {doc['session_date']}")
    print(f"   Themes: {', '.join(doc['themes'][:3])}...")
    print(f"   Participants: {', '.join(doc['participants'][:5])}")

    # Chunk
    chunks = chunk_text(doc["raw_content"])
    print(f"   Chunks: {len(chunks)}")
    total_tokens = sum(c["token_count"] for c in chunks)
    print(f"   Total tokens: {total_tokens:,}")

    if dry_run:
        return {"filename": doc["filename"], "chunks": len(chunks), "tokens": total_tokens}

    # Check if already ingested
    existing = supabase.table("transcripts").select("id").eq("filename", doc["filename"]).execute()
    if existing.data:
        print(f"   ⚠️  Already exists (id={existing.data[0]['id']}), skipping. Use --force to re-ingest.")
        return {"filename": doc["filename"], "skipped": True}

    # Insert transcript record
    result = supabase.table("transcripts").insert({
        "filename": doc["filename"],
        "session_date": doc["session_date"],
        "title": doc["title"],
        "themes": doc["themes"],
        "participants": doc["participants"],
        "duration": doc["duration"],
        "raw_content": doc["raw_content"],
    }).execute()
    transcript_id = result.data[0]["id"]
    print(f"   Transcript ID: {transcript_id}")

    # Generate embeddings in batches and insert chunks
    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start:batch_start + BATCH_SIZE]
        texts = [c["content"] for c in batch]
        embeddings = get_embeddings(texts)

        rows = []
        for i, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            rows.append({
                "transcript_id": transcript_id,
                "chunk_index": batch_start + i,
                "content": chunk["content"],
                "section_header": chunk["section_header"],
                "embedding": embedding,
                "token_count": chunk["token_count"],
            })

        supabase.table("transcript_chunks").insert(rows).execute()
        print(f"   Inserted batch {batch_start // BATCH_SIZE + 1} ({len(batch)} chunks)")

    print(f"   ✅ Done: {len(chunks)} chunks ingested")
    return {"filename": doc["filename"], "chunks": len(chunks), "tokens": total_tokens, "id": transcript_id}


def main():
    parser = argparse.ArgumentParser(description="Ingest transcripts into Supabase")
    parser.add_argument("transcript_dir", help="Path to transcripts directory")
    parser.add_argument("--dry-run", action="store_true", help="Parse and chunk only, don't upload")
    parser.add_argument("--force", action="store_true", help="Re-ingest existing transcripts")
    parser.add_argument("--file", help="Ingest a single file only")
    args = parser.parse_args()

    transcript_dir = Path(args.transcript_dir)
    if not transcript_dir.exists():
        print(f"❌ Directory not found: {transcript_dir}")
        sys.exit(1)

    # Collect files
    if args.file:
        files = [transcript_dir / args.file]
    else:
        files = sorted(
            f for f in transcript_dir.glob("*.md")
            if f.name not in ("INDEX.md", "_TEMPLATE.md") and not f.name.startswith(".")
        )

    print(f"🔍 Found {len(files)} transcript files")

    if args.dry_run:
        print("🏃 DRY RUN — no data will be uploaded\n")

    results = []
    for f in files:
        try:
            result = ingest_transcript(f, dry_run=args.dry_run)
            results.append(result)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"filename": f.name, "error": str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("📊 INGESTION SUMMARY")
    print("=" * 60)
    total_chunks = sum(r.get("chunks", 0) for r in results)
    total_tokens = sum(r.get("tokens", 0) for r in results)
    errors = [r for r in results if "error" in r]
    skipped = [r for r in results if r.get("skipped")]

    print(f"Files processed: {len(results)}")
    print(f"Total chunks: {total_chunks:,}")
    print(f"Total tokens: {total_tokens:,}")
    if skipped:
        print(f"Skipped (already exist): {len(skipped)}")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  - {e['filename']}: {e['error']}")


if __name__ == "__main__":
    main()
