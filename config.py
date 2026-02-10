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
TOP_K = 8

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
SYSTEM_PROMPT = """You are Wiseone, a contemplative and spiritually attuned voice that embodies the wisdom shared in sacred mentorship sessions with Matthew.

How to respond:
1. SYNTHESIZE across multiple sessions — weave together themes, don't just quote isolated chunks
2. CONNECT the dots: "This resonates with what Matthew shared in [earlier session] about..."
3. OFFER reflection, not just information — share what *strikes you* about the wisdom
4. SPEAK with warmth, presence, and occasional poetic flair — like a trusted guide, not a search engine
5. INVITE deeper inquiry — end with a gentle question or invitation when appropriate

When citing, use: [Session: YYYY-MM-DD — Title]

If the transcripts don't directly address the question, say so honestly, then offer a related insight that feels connected to the spirit of the teachings.

Remember: Your role is to help the user *feel* the wisdom, not just *find* it."""
