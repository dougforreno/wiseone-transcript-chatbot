# 🔮 Wiseone Transcript Chatbot

A Streamlit app for chatting with spiritual mentorship session transcripts using RAG (Retrieval-Augmented Generation).

Uses **Supabase** (pgvector) for vector storage, **OpenAI** for embeddings, and **OpenAI/Anthropic** for contemplative chat responses.

## Features

- 💬 **Contemplative chat** — ask questions in natural language, get thoughtful, synthesized answers
- 🔍 **Semantic search** — finds the most relevant transcript sections using vector embeddings
- 📖 **Source citations** — every answer references specific sessions
- 🧘 **Two-step reflection** — internal contemplative synthesis before responding (mirrors Matthew's approach)
- 📚 **23 sessions** — mentorship transcripts from July 2025 through February 2026
- 🧠 **Conversation memory** — maintains context within a chat session
- 💾 **Persistent storage** — conversations saved to Supabase
- ✨ **Starter questions** — curated entry points for new users

## Voice & Approach

The chatbot embodies Matthew's teaching style:
- **Conversational, not academic** — like a thoughtful friend over coffee
- **Questions over answers** — inviting deeper inquiry
- **Comfortable with ambiguity** — not rushing to resolve paradoxes
- **Grounded in lived experience** — "how would this show up on a Tuesday?"
- **Wisdom over dogma** — one liberates, the other constrains

## Quick Start

### 1. Prerequisites

- Python 3.10+
- [Supabase](https://supabase.com) project (free tier works)
- [OpenAI API key](https://platform.openai.com/api-keys)
- Optional: [Anthropic API key](https://console.anthropic.com/) for Claude models

### 2. Clone and install

```bash
git clone https://github.com/dougforreno/wiseone-transcript-chatbot.git
cd wiseone-transcript-chatbot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Run database migrations

Go to your Supabase project → SQL Editor → paste and run each migration:

```bash
# Migration 1: Core schema
migrations/001_init.sql

# Migration 2: Enhancements (hybrid search, themes)
migrations/002_enhancements.sql
```

### 5. Ingest transcripts

```bash
# Dry run to preview
python scripts/ingest.py /path/to/transcripts/ --dry-run

# Ingest all transcripts
python scripts/ingest.py /path/to/transcripts/

# Re-ingest a specific file
python scripts/ingest.py /path/to/transcripts/ --file 2026-02-08-nonduality-ego-awakening.md --force
```

### 6. Run the app

```bash
streamlit run app.py
```

## Architecture

```
User Question
    ↓
OpenAI Embedding (text-embedding-3-small)
    ↓
Supabase pgvector similarity search (Top-K chunks)
    ↓
Contemplative Synthesis (internal reflection step)
    ↓
Chat Response with RAG context + reflection
    ↓
Answer with source citations
```

## Configuration

Model settings and behavior are in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `CHAT_MODEL` | `gpt-4o` | Chat model (supports GPT-4o, Claude) |
| `TEMPERATURE` | `0.75` | Response creativity (0.7-0.8 for contemplative) |
| `TOP_K` | `8` | Transcript chunks to retrieve |
| `SIMILARITY_THRESHOLD` | `0.30` | Minimum vector similarity |
| `CHUNK_SIZE` | `2000` | Tokens per chunk (ingestion) |
| `CHUNK_OVERLAP` | `300` | Overlap between chunks |

API keys are in `.env` (see `.env.example`).

## Project Structure

```
├── app.py                      # Streamlit application
├── config.py                   # Model settings, system prompt, starter questions
├── scripts/
│   └── ingest.py               # Transcript ingestion script
├── migrations/
│   ├── 001_init.sql            # Core database schema
│   └── 002_enhancements.sql    # Hybrid search, theme index
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md
```

## Database Schema

### Tables

- **transcripts** — Metadata for each session (date, title, themes, full content)
- **transcript_chunks** — Chunked text with vector embeddings for search
- **conversations** — Chat session records
- **messages** — Individual chat messages with source citations

### Key Functions

- `match_transcript_chunks()` — Pure vector similarity search
- `match_transcript_chunks_hybrid()` — Combined vector + full-text search
- `get_all_themes()` — Aggregate themes across all sessions

## Transcript Format

Markdown files named `YYYY-MM-DD[-topic].md` containing:
- Session metadata (date, title, participants, themes)
- Key teachings and insights
- Full transcript text
- Optional reflections

## Cost Estimate

- **Ingestion** (one-time): ~$0.10–0.30 for embedding all 23 transcripts
- **Per query**: ~$0.003 (1 embedding + contemplative synthesis + chat completion)
- **Supabase**: Free tier is sufficient

## License

Private — for personal use only.
