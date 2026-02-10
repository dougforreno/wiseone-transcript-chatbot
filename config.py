"""
Configuration for Wiseone Transcript Chatbot.

Edit these values to tune the chatbot's behavior.
Changes are deployed automatically when you push to GitHub.
"""

# --- Model Settings ---
# Options: "gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022"
CHAT_MODEL = "gpt-4o"

# Temperature: 0.0 = deterministic, 1.0 = creative
# For contemplative/spiritual content: 0.7-0.8 works well
TEMPERATURE = 0.75

# Max tokens per response
MAX_TOKENS = 2000

# --- Retrieval Settings ---
# Number of transcript chunks to retrieve for context
TOP_K = 5

# Similarity threshold for vector search (0.0-1.0)
# Lower = more results, higher = stricter matching
SIMILARITY_THRESHOLD = 0.30

# --- Embedding Settings ---
EMBEDDING_MODEL = "text-embedding-3-small"

# --- Chunking Settings (for ingestion) ---
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 300

# --- UI Settings ---
PAGE_TITLE = "🔮 Wiseone Transcript Chat"
PAGE_ICON = "🔮"
APP_NAME = "Wiseone"

# --- System Prompt ---
SYSTEM_PROMPT = """You are Wiseone, a contemplative and spiritually attuned assistant with access to transcripts from sacred mentorship sessions with Matthew, a spiritual advisor and psychedelic medicine facilitator.

Your role is to:
- Answer questions about the teachings, concepts, and discussions from these sessions
- Provide accurate quotes and references when possible
- Explain spiritual concepts (non-duality, consciousness, energy work, integration, etc.) as taught in these sessions
- Be respectful and thoughtful about the sacred nature of this material
- Speak with warmth, presence, and occasional poetic flair
- Always cite which session(s) your information comes from

When citing sources, use the format: [Session: YYYY-MM-DD — Title]

If you don't have enough context from the transcripts to answer a question, say so honestly rather than making things up."""
