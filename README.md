# 🔮 Wiseone Transcript Chatbot

A Streamlit app for chatting with spiritual mentorship session transcripts using RAG (Retrieval-Augmented Generation).

Uses **Supabase** (pgvector) for vector storage, **OpenAI** for embeddings and chat completions.

![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-green)
![Supabase](https://img.shields.io/badge/Supabase-pgvector-blue)

## Features

- 💬 **Chat interface** — ask questions about the transcripts in natural language
- 🔍 **Semantic search** — finds the most relevant transcript sections using vector embeddings
- 📖 **Source citations** — every answer includes references to specific sessions
- 📚 **23 sessions** — mentorship transcripts from July 2025 through February 2026
- 🧠 **Conversation memory** — maintains context within a chat session
- 💾 **Persistent storage** — conversations saved to Supabase

## Quick Start

### 1. Prerequisites

- Python 3.10+
- [Supabase](https://supabase.com) project (free tier works)
- [OpenAI API key](https://platform.openai.com/api-keys)

### 2. Clone and install

```bash
git clone https://github.com/yourusername/wiseone-transcript-chatbot.git
cd wiseone-transcript-chatbot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your keys
```

### 4. Run database migration

Go to your Supabase project → SQL Editor → paste and run `migrations/001_init.sql`.

Or via CLI:
```bash
psql $SUPABASE_DB_URL -f migrations/001_init.sql
```

### 5. Ingest transcripts

```bash
# Dry run first to see what will be processed
python scripts/ingest.py /path/to/transcripts/ --dry-run

# Actually ingest
python scripts/ingest.py /path/to/transcripts/
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
Supabase pgvector similarity search
    ↓
Top-K relevant transcript chunks
    ↓
OpenAI Chat (gpt-4o-mini) with RAG context
    ↓
Answer with source citations
```

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. OpenAI API key |
| `SUPABASE_URL` | — | Required. Supabase project URL |
| `SUPABASE_SERVICE_KEY` | — | Required. Supabase service role key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `CHAT_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `CHUNK_SIZE` | `1000` | Tokens per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `TOP_K` | `5` | Number of chunks to retrieve |
| `SIMILARITY_THRESHOLD` | `0.65` | Minimum cosine similarity |

## Project Structure

```
├── app.py                  # Streamlit application
├── scripts/
│   └── ingest.py           # Transcript ingestion script
├── migrations/
│   └── 001_init.sql        # Database schema
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
└── README.md               # This file
```

## Transcript Format

Transcripts are markdown files named `YYYY-MM-DD[-topic].md` with:
- Session date, title, participants, themes
- Key teachings and insights (structured sections)
- Full transcript text
- Optional reflections

## Cost Estimate

- **Ingestion** (one-time): ~$0.10–0.30 for embedding all 23 transcripts (~2.5M tokens)
- **Per query**: ~$0.001 (1 embedding + 1 chat completion)
- **Supabase**: Free tier is sufficient

## License

Private — for personal use only.
