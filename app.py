"""
Wiseone Transcript Chatbot — Streamlit App

Chat with spiritual mentorship transcripts using RAG (Retrieval-Augmented Generation).
Uses Supabase pgvector for semantic search and OpenAI/Anthropic for embeddings + chat.
"""

import os
import json
from datetime import datetime

import streamlit as st
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv

import config

load_dotenv()

# --- Config (from config.py for easy iteration) ---
EMBEDDING_MODEL = config.EMBEDDING_MODEL
CHAT_MODEL = config.CHAT_MODEL
TEMPERATURE = config.TEMPERATURE
MAX_TOKENS = config.MAX_TOKENS
TOP_K = config.TOP_K
SIMILARITY_THRESHOLD = config.SIMILARITY_THRESHOLD
SYSTEM_PROMPT = config.SYSTEM_PROMPT

# --- Initialize clients ---
@st.cache_resource
def init_clients():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    supabase_client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )
    
    # Initialize Anthropic if key available and model is Claude
    anthropic_client = None
    if "claude" in CHAT_MODEL.lower():
        try:
            import anthropic
            anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        except ImportError:
            st.error("Anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            st.warning(f"Anthropic client init failed: {e}")
    
    return openai_client, supabase_client, anthropic_client


def get_embedding(client: OpenAI, text: str) -> list[float]:
    """Generate embedding for a query."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def search_transcripts(supabase_client, query_embedding: list[float], top_k: int = TOP_K) -> list[dict]:
    """Search for relevant transcript chunks using vector similarity."""
    result = supabase_client.rpc(
        "match_transcript_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": SIMILARITY_THRESHOLD,
            "match_count": top_k,
        },
    ).execute()
    return result.data


def build_context(chunks: list[dict]) -> str:
    """Build context string from retrieved chunks."""
    if not chunks:
        return "No relevant transcript sections found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        session_date = chunk.get("session_date", "Unknown date")
        title = chunk.get("title", "Untitled session")
        section = chunk.get("section_header", "")
        similarity = chunk.get("similarity", 0)

        header = f"[Source {i}: {session_date} — {title}"
        if section:
            header += f" > {section}"
        header += f" (relevance: {similarity:.0%})]"

        context_parts.append(f"{header}\n{chunk['content']}")

    return "\n\n---\n\n".join(context_parts)


def format_sources(chunks: list[dict]) -> list[dict]:
    """Format source citations for display."""
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk.get("session_date"), chunk.get("title"))
        if key not in seen:
            seen.add(key)
            sources.append({
                "date": chunk.get("session_date", "Unknown"),
                "title": chunk.get("title", "Untitled"),
                "section": chunk.get("section_header", ""),
                "similarity": chunk.get("similarity", 0),
            })
    return sources


def chat_completion(openai_client, anthropic_client, messages: list[dict], context: str) -> str:
    """Generate chat response with RAG context using OpenAI or Anthropic."""
    system_msg = SYSTEM_PROMPT + f"\n\n---\nRelevant transcript context:\n\n{context}"
    
    # Include last 10 messages for conversation context
    recent_messages = messages[-10:]

    # Use Anthropic for Claude models
    if anthropic_client and "claude" in CHAT_MODEL.lower():
        # Convert messages to Anthropic format
        anthropic_messages = []
        for m in recent_messages:
            role = "user" if m["role"] == "user" else "assistant"
            anthropic_messages.append({"role": role, "content": m["content"]})
        
        response = anthropic_client.messages.create(
            model=CHAT_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_msg,
            messages=anthropic_messages,
        )
        return response.content[0].text
    
    # Use OpenAI for GPT models
    full_messages = [{"role": "system", "content": system_msg}]
    full_messages.extend(recent_messages)

    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=full_messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content


def save_message(supabase_client, conversation_id: str, role: str, content: str, sources: list = None):
    """Save a message to the database."""
    try:
        supabase_client.table("messages").insert({
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": json.dumps(sources) if sources else None,
        }).execute()
    except Exception:
        pass  # Non-critical, don't break chat


def create_conversation(supabase_client, title: str = None) -> str:
    """Create a new conversation and return its ID."""
    try:
        result = supabase_client.table("conversations").insert({
            "title": title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        }).execute()
        return result.data[0]["id"]
    except Exception:
        import uuid
        return str(uuid.uuid4())


def get_transcript_stats(supabase_client) -> dict:
    """Get stats about ingested transcripts."""
    try:
        transcripts = supabase_client.table("transcripts").select("id, filename, session_date, title, themes").order("session_date").execute()
        chunks = supabase_client.table("transcript_chunks").select("id", count="exact").execute()
        return {
            "transcripts": transcripts.data,
            "transcript_count": len(transcripts.data),
            "chunk_count": chunks.count,
        }
    except Exception as e:
        return {"error": str(e), "transcript_count": 0, "chunk_count": 0}


# --- Streamlit UI ---

def main():
    st.set_page_config(
        page_title="Wiseone Transcript Chat",
        page_icon="🔮",
        layout="wide",
    )

    st.title("🔮 Wiseone Transcript Chat")
    st.caption("Chat with spiritual mentorship session transcripts")

    openai_client, supabase_client, anthropic_client = init_clients()

    # --- Sidebar ---
    with st.sidebar:
        st.header("📚 Transcript Library")

        stats = get_transcript_stats(supabase_client)
        if "error" not in stats:
            st.metric("Sessions", stats["transcript_count"])
            st.metric("Searchable Chunks", stats["chunk_count"])

            if stats["transcripts"]:
                st.divider()
                st.subheader("Sessions")
                for t in stats["transcripts"]:
                    themes = ", ".join((t.get("themes") or [])[:2])
                    label = f"**{t['session_date']}**"
                    if t.get("title"):
                        # Truncate long titles
                        title = t["title"][:60] + "..." if len(t["title"]) > 60 else t["title"]
                        label += f"\n{title}"
                    if themes:
                        label += f"\n_{themes}_"
                    st.markdown(label, unsafe_allow_html=False)
                    st.caption("")  # spacing
        else:
            st.warning(f"Could not load stats: {stats['error']}")
            st.info("Make sure you've run the migration and ingestion scripts.")

        st.divider()
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_id = create_conversation(supabase_client)
            st.rerun()

        st.divider()
        st.caption("Settings")
        top_k = st.slider("Sources to retrieve", 1, 10, TOP_K, key="top_k")
        show_sources = st.checkbox("Show source details", value=True, key="show_sources")

    # --- Init session state ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = create_conversation(supabase_client)

    # --- Display chat history ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources") and show_sources:
                with st.expander("📖 Sources"):
                    for src in msg["sources"]:
                        st.markdown(
                            f"- **{src['date']}** — {src['title']}"
                            + (f" > {src['section']}" if src.get('section') else "")
                            + f" ({src['similarity']:.0%} match)"
                        )

    # --- Chat input ---
    if prompt := st.chat_input("Ask about the transcripts..."):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching transcripts..."):
                # Get embedding for query
                query_embedding = get_embedding(openai_client, prompt)

                # Search for relevant chunks
                chunks = search_transcripts(supabase_client, query_embedding, top_k=top_k)

                # Build context
                context = build_context(chunks)
                sources = format_sources(chunks)

            with st.spinner("Thinking..."):
                # Build message history for API
                api_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]

                # Generate response
                response = chat_completion(openai_client, anthropic_client, api_messages, context)

            st.markdown(response)

            if sources and show_sources:
                with st.expander("📖 Sources"):
                    for src in sources:
                        st.markdown(
                            f"- **{src['date']}** — {src['title']}"
                            + (f" > {src['section']}" if src.get('section') else "")
                            + f" ({src['similarity']:.0%} match)"
                        )

        # Save to state and DB
        msg_data = {"role": "assistant", "content": response, "sources": sources}
        st.session_state.messages.append(msg_data)

        save_message(supabase_client, st.session_state.conversation_id, "user", prompt)
        save_message(supabase_client, st.session_state.conversation_id, "assistant", response, sources)


if __name__ == "__main__":
    main()
