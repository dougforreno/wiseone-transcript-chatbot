#!/usr/bin/env python3
"""
Upload a transcript to Supabase with chunking and embeddings.
"""
import os
import re
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

# Load env from wiseone project
load_dotenv("/Users/dougerwin/clawd/projects/wiseone-transcript-chatbot/.env")

# Config
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "text-embedding-3-small"


def init_clients():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    supabase_client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )
    return openai_client, supabase_client


def parse_transcript(filepath: str) -> dict:
    """Parse the transcript markdown file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract metadata from the file
    metadata = {}
    
    # Title from first heading
    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()
    
    # Date
    date_match = re.search(r'\*\*Date:\*\* (.+)$', content, re.MULTILINE)
    if date_match:
        date_str = date_match.group(1).strip()
        # Parse "2026-02-18 00:20 (local)"
        date_part = date_str.split()[0]
        metadata['session_date'] = date_part
    
    # Granola meeting id
    granola_match = re.search(r'\*\*Granola meeting id:\*\* (.+)$', content, re.MULTILINE)
    if granola_match:
        metadata['granola_meeting_id'] = granola_match.group(1).strip()
    
    # Participants
    participants_match = re.search(r'\*\*Participants \(known\):\*\* (.+)$', content, re.MULTILINE)
    if participants_match:
        participants_str = participants_match.group(1).strip()
        metadata['participants'] = [p.strip() for p in participants_str.split(',')]
    else:
        metadata['participants'] = []
    
    # Extract raw content (everything after the frontmatter)
    lines = content.split('\n')
    in_frontmatter = True
    content_lines = []
    for line in lines:
        if in_frontmatter and line.startswith('## '):
            in_frontmatter = False
        if not in_frontmatter or line.startswith('## ') or line.startswith('Transcript:'):
            in_frontmatter = False
        if not in_frontmatter:
            content_lines.append(line)
    
    # Get full transcript section
    transcript_match = re.search(r'## Transcript\n\n(.+)', content, re.DOTALL)
    if transcript_match:
        metadata['raw_content'] = transcript_match.group(1).strip()
    else:
        # Fallback to everything after summary
        metadata['raw_content'] = '\n'.join(content_lines).strip()
    
    # Extract themes from summary section
    themes = []
    summary_section = re.search(r'## Summary.*?\n\n(## Transcript|$)', content, re.DOTALL)
    if summary_section:
        summary_text = summary_section.group(0)
        # Extract section headers from summary
        section_matches = re.findall(r'### (.+)$', summary_text, re.MULTILINE)
        themes = [s.strip() for s in section_matches]
    
    metadata['themes'] = themes if themes else ['spiritual dynamics', 'consciousness', 'presence']
    
    return metadata


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to end at a sentence or paragraph boundary
        if end < len(text):
            # Look for sentence endings
            for delim in ['.\n', '. ', '! ', '? ', '\n\n']:
                last_delim = chunk.rfind(delim)
                if last_delim > chunk_size * 0.5:  # At least half the chunk
                    end = start + last_delim + len(delim)
                    chunk = text[start:end]
                    break
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks


def get_embedding(client: OpenAI, text: str) -> list[float]:
    """Generate embedding for text."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def upload_transcript(filepath: str):
    """Upload transcript to Supabase."""
    openai_client, supabase = init_clients()
    
    # Parse the file
    print(f"Parsing {filepath}...")
    metadata = parse_transcript(filepath)
    
    filename = Path(filepath).name
    
    # Check if already exists
    existing = supabase.table("transcripts").select("id").eq("filename", filename).execute()
    if existing.data:
        print(f"Transcript {filename} already exists. Skipping.")
        return
    
    # Insert transcript
    print(f"Inserting transcript: {metadata.get('title', filename)}...")
    transcript_data = {
        "filename": filename,
        "session_date": metadata.get("session_date"),
        "title": metadata.get("title", filename),
        "themes": metadata.get("themes", []),
        "participants": metadata.get("participants", []),
        "duration": None,
        "raw_content": metadata.get("raw_content", "")
    }
    
    result = supabase.table("transcripts").insert(transcript_data).execute()
    transcript_id = result.data[0]["id"]
    print(f"Created transcript with ID: {transcript_id}")
    
    # Chunk and embed
    raw_content = metadata.get("raw_content", "")
    if not raw_content:
        print("No content to chunk!")
        return
    
    chunks = chunk_text(raw_content)
    print(f"Created {len(chunks)} chunks")
    
    # Insert chunks with embeddings
    for i, chunk_content in enumerate(chunks):
        print(f"  Processing chunk {i+1}/{len(chunks)}...")
        
        # Generate embedding
        embedding = get_embedding(openai_client, chunk_content)
        
        chunk_data = {
            "transcript_id": transcript_id,
            "chunk_index": i,
            "content": chunk_content,
            "section_header": "Full Transcript" if i == 0 else "",
            "embedding": embedding,
            "token_count": len(chunk_content.split())  # Rough estimate
        }
        
        supabase.table("transcript_chunks").insert(chunk_data).execute()
    
    print(f"✅ Successfully uploaded {filename} with {len(chunks)} chunks!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        filepath = "/Users/dougerwin/clawd/notes/wisdom/transcripts/2026-02-18_granola_advanced-spiritual-dynamics-group.md"
    else:
        filepath = sys.argv[1]
    
    upload_transcript(filepath)
