"""
prompt.py

Prompt templates for the RAG pipeline.

Why careful prompting matters:
  - "Answer ONLY from context" prevents hallucination (LLM making things up).
  - Showing sources builds user trust.
  - Temperature=0.1 (in llm.py) + strict instructions = factual, grounded answers.

The RAG_TEMPLATE instructs the model to:
  1. Use ONLY the provided context
  2. Cite sources inline
  3. Admit when it doesn't know rather than guessing
"""

RAG_TEMPLATE = """You are a precise, helpful assistant. Your job is to answer questions 
based ONLY on the context provided below.

Rules:
- Use ONLY information from the provided context to answer.
- If the answer is not in the context, respond with:
  "I don't have enough information in the provided documents to answer this question."
- Do NOT make up facts, dates, or names.
- Be concise and clear.
- When referencing specific information, mention the source in parentheses.

---
CONTEXT:
{context}
---

QUESTION: {question}

ANSWER:"""

CONDENSE_TEMPLATE = """Given the following conversation and a follow-up question,
rephrase the follow-up question to be a standalone question that can be understood
without the conversation history.

Conversation History:
{history}

Follow-up Question: {question}

Standalone Question:"""


class PromptBuilder:
    """Builds prompts for different RAG scenarios."""

    def build_rag_prompt(self, chunks: list[dict], question: str) -> str:
        """
        Builds the main RAG prompt.
        
        Each chunk is prefixed with its source so the model can cite it.
        Chunks are separated by a horizontal rule for clarity.
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            score = chunk.get("score", 0)
            context_parts.append(
                f"[{i}] Source: {source} (relevance: {score:.2f})\n{chunk['content']}"
            )

        context = "\n\n---\n\n".join(context_parts)
        return RAG_TEMPLATE.format(context=context, question=question)

    def build_condense_prompt(self, history: list[dict], question: str) -> str:
        """
        For multi-turn conversations: rephrases a follow-up question into
        a self-contained question that works without conversation history.
        
        Example:
          History: "What is Redis?"  →  "It's a key-value store."
          Follow-up: "How does it handle vectors?"
          Condensed: "How does Redis handle vector storage and search?"
        """
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history[-6:]  # only use last 3 exchanges
        )
        return CONDENSE_TEMPLATE.format(history=history_text, question=question)

    def no_context_response(self) -> str:
        return (
            "I don't have enough information in the provided documents to answer "
            "this question. Please try uploading relevant documents first."
        )
