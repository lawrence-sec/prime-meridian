# ingest.py
# Prime Meridian — PDF/TXT ingestion pipeline
# Prompts for cert on start, chunks, embeds with Voyage AI, stores in Pinecone

import os
import glob
import time
import json
from dotenv import load_dotenv
import voyageai
from pinecone import Pinecone
from PyPDF2 import PdfReader
from tqdm import tqdm

load_dotenv()

# --- Config ---
VOYAGE_API_KEY   = os.getenv("VOYAGE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST    = os.getenv("PINECONE_HOST")
INDEX_NAME       = os.getenv("PINECONE_INDEX_NAME", "prime-meridian")
EMBED_MODEL      = "voyage-3-lite"
CHUNK_SIZE       = 512
CHUNK_OVERLAP    = 64
RATE_LIMIT_DELAY = 1
INGESTED_LOG     = "ingested.json"

CERTS = {
    "1": ("security-plus", "Security+"),
    "2": ("network-plus",  "Network+"),
    "3": ("linux-plus",    "Linux+"),
    "4": ("cysa-plus",     "CySA+"),
    "5": ("pentest-plus",  "PenTest+")
}

# --- Clients ---
voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
pc     = Pinecone(api_key=PINECONE_API_KEY)
index  = pc.Index(host=PINECONE_HOST)


# ── Cert Selection ────────────────────────────────────────────────────────────

def select_cert():
    print("\nWhich certification is this content for?\n")
    for num, (_, label) in CERTS.items():
        print(f"  {num}. {label}")
    print()
    while True:
        choice = input("Enter number: ").strip()
        if choice in CERTS:
            return CERTS[choice]
        print("Invalid. Enter 1-5.")


# ── Tracking ──────────────────────────────────────────────────────────────────

def load_ingested():
    if os.path.exists(INGESTED_LOG):
        with open(INGESTED_LOG) as f:
            return set(json.load(f))
    return set()

def save_ingested(ingested):
    with open(INGESTED_LOG, "w") as f:
        json.dump(list(ingested), f, indent=2)


# ── Extract ───────────────────────────────────────────────────────────────────

def extract_text(file_path):
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


# ── Chunk ─────────────────────────────────────────────────────────────────────

def chunk_text(text, source):
    chunks, start, idx = [], 0, 0
    while start < len(text):
        chunk = text[start:start + CHUNK_SIZE].strip()
        if chunk:
            chunks.append({
                "id":     f"{source}_{idx}",
                "text":   chunk,
                "source": source
            })
            idx += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# ── Embed + Upsert ────────────────────────────────────────────────────────────

def embed_and_upsert(chunks, cert, cert_label):
    batch_size = 64
    for i in tqdm(range(0, len(chunks), batch_size), desc="  Embedding + uploading"):
        batch      = chunks[i:i + batch_size]
        texts      = [c["text"] for c in batch]
        result     = voyage.embed(texts, model=EMBED_MODEL, input_type="document")
        embeddings = result.embeddings
        vectors    = [{
            "id":     c["id"],
            "values": e,
            "metadata": {
                "text":       c["text"],
                "source":     c["source"],
                "cert":       cert,
                "cert_label": cert_label
            }
        } for c, e in zip(batch, embeddings)]
        index.upsert(vectors=vectors)
        time.sleep(RATE_LIMIT_DELAY)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=================================")
    print("  Prime Meridian Ingestion Pipeline")
    print("=================================")

    cert, cert_label = select_cert()
    print(f"\nTagging all files as: {cert_label}\n")

    all_files = (
        glob.glob("study-materials/*.pdf") +
        glob.glob("study-materials/*.txt")
    )

    if not all_files:
        print("No files found in study-materials/")
        return

    ingested  = load_ingested()
    new_files = [f for f in all_files if os.path.basename(f) not in ingested]
    skipped   = [f for f in all_files if os.path.basename(f) in ingested]

    print(f"Found {len(all_files)} file(s) total")
    print(f"  -> {len(skipped)} already ingested — skipping")
    print(f"  -> {len(new_files)} new file(s) to process\n")

    if not new_files:
        print("Nothing new to ingest. Add files to study-materials/ and run again.")
        return

    for file_path in new_files:
        filename = os.path.basename(file_path)
        source   = os.path.splitext(filename)[0]
        print(f"Processing: {filename}")

        text = extract_text(file_path)
        print(f"  Extracted {len(text)} characters")

        chunks = chunk_text(text, source)
        print(f"  Created {len(chunks)} chunks")

        embed_and_upsert(chunks, cert, cert_label)

        ingested.add(filename)
        save_ingested(ingested)
        print(f"  Ingested as {cert_label}\n")

    print("Done. All new documents ingested into Prime Meridian.")


if __name__ == "__main__":
    main()
