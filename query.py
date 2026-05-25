# query.py
# Prime Meridian — Query engine
# Embeds question with Voyage, retrieves from Pinecone, answers with Claude

import os
from dotenv import load_dotenv
import voyageai
from pinecone import Pinecone
import anthropic

load_dotenv()

# --- Config ---
VOYAGE_API_KEY   = os.getenv("VOYAGE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST    = os.getenv("PINECONE_HOST")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EMBED_MODEL      = "voyage-3-lite"
TOP_K            = 8  # number of chunks to retrieve

# --- Clients ---
voyage    = voyageai.Client(api_key=VOYAGE_API_KEY)
pc        = Pinecone(api_key=PINECONE_API_KEY)
index     = pc.Index(host=PINECONE_HOST)
claude    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are Prime Meridian, an expert study assistant for CompTIA certifications.

You answer questions using ONLY the study material provided to you in the context below.
- Be direct and specific
- Use bullet points for lists
- If the answer is not in the context, say so clearly — do not guess
- Always mention which certification the answer relates to (Security+, Linux+, Network+)
- End every answer with a one-line exam tip if relevant"""


def retrieve(question, top_k=TOP_K):
    """Embed the question and retrieve top matching chunks from Pinecone."""
    result     = voyage.embed([question], model=EMBED_MODEL, input_type="query")
    embedding  = result.embeddings[0]
    matches    = index.query(vector=embedding, top_k=top_k, include_metadata=True)
    return matches.matches


def build_context(matches):
    """Format retrieved chunks into a context string."""
    context = ""
    for i, match in enumerate(matches):
        source = match.metadata.get("source", "unknown")
        text   = match.metadata.get("text", "")
        context += f"[{i+1}] Source: {source}\n{text}\n\n"
    return context.strip()


def ask(question):
    """Full RAG pipeline — retrieve, build context, ask Claude."""
    print(f"\nQuestion: {question}")
    print("-" * 50)

    matches = retrieve(question)
    if not matches:
        print("No relevant content found in your study materials.")
        return

    context = build_context(matches)

    user_message = f"""Context from study materials:

{context}

---

Question: {question}"""

    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    answer = response.content[0].text
    print(f"\n{answer}\n")
    return answer


def main():
    print("=================================")
    print("  Prime Meridian Query Engine")
    print("=================================")
    print("Type your question. Type 'exit' to quit.\n")

    while True:
        question = input("Ask: ").strip()
        if not question:
            continue
        if question.lower() in ["exit", "quit", "q"]:
            print("Session ended.")
            break
        ask(question)


if __name__ == "__main__":
    main()
