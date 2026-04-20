"""
app.py  —  Streamlit Chat UI

A clean, production-style chat interface for the RAG API.

Features:
  - Chat history with user/assistant messages
  - File upload (PDF, TXT, DOCX) with ingestion feedback
  - Source citations shown under each answer
  - Cache hit indicator (⚡ = instant cached response)
  - Health status in sidebar
  - Streaming support via the /query/stream endpoint
"""

import streamlit as st
import httpx
import json

API_BASE = "http://localhost:8000"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RAG Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .source-badge {
        display: inline-block;
        background: #1f3a5f;
        color: #7fb3e8;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        margin: 2px;
    }
    .cache-badge {
        display: inline-block;
        background: #1f4a2f;
        color: #7fd87f;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
    }
    .stChatMessage { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ingested_sources" not in st.session_state:
    st.session_state.ingested_sources = []


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 RAG Assistant")
    st.caption("Powered by Redis · Ollama · sentence-transformers")
    st.divider()

    # Health status
    st.subheader("System Health")
    try:
        resp = httpx.get(f"{API_BASE}/health/", timeout=5)
        h = resp.json()
        col1, col2 = st.columns(2)
        with col1:
            redis_icon = "🟢" if h["redis"] == "ok" else "🔴"
            st.metric("Redis", f"{redis_icon} {h['redis']}")
            st.metric("Docs indexed", h["index_docs"])
        with col2:
            ollama_icon = "🟢" if h["ollama"] == "ok" else "🔴"
            st.metric("Ollama", f"{ollama_icon} {h['ollama']}")
    except Exception:
        st.error("API not reachable. Start with: `uvicorn api.main:app --reload`")

    st.divider()

    # File uploader
    st.subheader("Upload Documents")
    uploaded_file = st.file_uploader(
        "Upload PDF, TXT, DOCX, or MD",
        type=["pdf", "txt", "docx", "md"],
        help="Your document will be chunked, embedded, and stored in Redis.",
    )
    if uploaded_file:
        if st.button("Ingest Document", use_container_width=True):
            with st.spinner(f"Ingesting {uploaded_file.name}..."):
                try:
                    resp = httpx.post(
                        f"{API_BASE}/ingest/file",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.success(
                            f"✅ Ingested **{data['chunks_stored']}** chunks "
                            f"from `{data['source']}`"
                        )
                        st.session_state.ingested_sources.append(data["source"])
                        st.rerun()
                    else:
                        st.error(f"Ingestion failed: {resp.json().get('detail')}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Paste text
    st.divider()
    st.subheader("Or Paste Text")
    text_input = st.text_area("Paste document text here", height=150, key="paste_text")
    text_source = st.text_input("Source name", placeholder="e.g. my-doc", key="paste_source")
    if st.button("Ingest Text", use_container_width=True, disabled=not (text_input and text_source)):
        with st.spinner("Ingesting..."):
            try:
                resp = httpx.post(
                    f"{API_BASE}/ingest/text",
                    json={"text": text_input, "source": text_source},
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"✅ Ingested {data['chunks_stored']} chunks")
                    st.session_state.ingested_sources.append(data["source"])
                else:
                    st.error(f"Failed: {resp.json().get('detail')}")
            except Exception as e:
                st.error(f"Error: {e}")

    # Source filter
    st.divider()
    st.subheader("Query Settings")
    source_filter = st.selectbox(
        "Filter by source (optional)",
        options=["All sources"] + st.session_state.ingested_sources,
        index=0,
    )
    top_k = st.slider("Chunks to retrieve (top-k)", min_value=1, max_value=10, value=5)

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Main Chat Area ─────────────────────────────────────────────────────────────
st.header("Ask a question about your documents")
st.caption("Type below. Answers are grounded in your uploaded documents only.")

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.markdown("**Sources:**")
            badges = " ".join(
                f'<span class="source-badge">📄 {s["source"]} ({s["score"]:.0%})</span>'
                for s in msg["sources"]
            )
            st.markdown(badges, unsafe_allow_html=True)
        if msg.get("cached"):
            st.markdown(
                '<span class="cache-badge">⚡ Cached response</span>',
                unsafe_allow_html=True,
            )

# Chat input
if user_input := st.chat_input("Ask a question about your documents..."):
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build query request
    query_payload = {
        "question": user_input,
        "top_k": top_k,
        "source_filter": None if source_filter == "All sources" else source_filter,
    }

    # Call API and stream the response
    with st.chat_message("assistant"):
        answer_container = st.empty()
        full_answer = ""

        try:
            # Use streaming endpoint for live token output
            with httpx.stream(
                "POST",
                f"{API_BASE}/query/stream",
                json=query_payload,
                timeout=180,
            ) as resp:
                for chunk in resp.iter_text():
                    full_answer += chunk
                    answer_container.markdown(full_answer + "▌")  # typing cursor

            answer_container.markdown(full_answer)
            cached = False
            sources = []

        except Exception:
            # Fallback to non-streaming if stream fails
            try:
                resp = httpx.post(
                    f"{API_BASE}/query/",
                    json=query_payload,
                    timeout=180,
                )
                data = resp.json()
                full_answer = data["answer"]
                cached = data["cached"]
                sources = data.get("sources", [])
                answer_container.markdown(full_answer)
            except Exception as e:
                full_answer = f"Error: {e}"
                cached = False
                sources = []
                answer_container.error(full_answer)

        # Show sources
        if sources:
            st.markdown("**Sources:**")
            badges = " ".join(
                f'<span class="source-badge">📄 {s["source"]} ({s["score"]:.0%})</span>'
                for s in sources
            )
            st.markdown(badges, unsafe_allow_html=True)

        if cached:
            st.markdown(
                '<span class="cache-badge">⚡ Cached response</span>',
                unsafe_allow_html=True,
            )

    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_answer,
        "sources": sources,
        "cached": cached,
    })
