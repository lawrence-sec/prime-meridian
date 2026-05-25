# add_videos.py
# Prime Meridian — YouTube batch ingestion
# Prompts for cert on start, downloads, cleans, and ingests into Pinecone

import os
import re
import sys
import time
import json
import subprocess
from dotenv import load_dotenv
import voyageai
from pinecone import Pinecone
from tqdm import tqdm

load_dotenv()

# --- Config ---
VOYAGE_API_KEY   = os.getenv("VOYAGE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST    = os.getenv("PINECONE_HOST")
EMBED_MODEL      = "voyage-3-lite"
CHUNK_SIZE       = 512
CHUNK_OVERLAP    = 64
RATE_LIMIT_DELAY = 1
INGESTED_LOG     = "ingested.json"
STUDY_DIR        = "study-materials"

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


# ── Download ──────────────────────────────────────────────────────────────────

def get_video_ids(url):
    result = subprocess.run(
        ["python", "-m", "yt_dlp", "--flat-playlist", "--print", "id", url],
        capture_output=True, text=True
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def get_video_title(video_id):
    result = subprocess.run(
        ["python", "-m", "yt_dlp", "--print", "title",
         f"https://www.youtube.com/watch?v={video_id}"],
        capture_output=True, text=True
    )
    title = result.stdout.strip()
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'\s+', '-', title).lower()
    return title[:60] if title else video_id

def download_srt(video_id, output_stem):
    subprocess.run([
        "python", "-m", "yt_dlp",
        "--write-auto-sub", "--skip-download",
        "--sub-format", "ttml", "--convert-subs", "srt",
        "-o", output_stem,
        f"https://www.youtube.com/watch?v={video_id}"
    ], capture_output=True)


# ── Clean ─────────────────────────────────────────────────────────────────────

def clean_srt(srt_path, txt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    clean = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', content)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = '\n'.join(line for line in clean.splitlines() if line.strip())
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(clean)
    return len(clean)


# ── Ingest ────────────────────────────────────────────────────────────────────

def chunk_text(text, source):
    chunks, start, idx = [], 0, 0
    while start < len(text):
        chunk = text[start:start + CHUNK_SIZE].strip()
        if chunk:
            chunks.append({"id": f"{source}_{idx}", "text": chunk, "source": source})
            idx += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

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
    print("  Prime Meridian — Add Videos")
    print("=================================")

    if len(sys.argv) < 2:
        print("Usage: python add_videos.py <url1> <url2> ...")
        return

    cert, cert_label = select_cert()
    print(f"\nTagging all videos as: {cert_label}\n")

    urls     = sys.argv[1:]
    ingested = load_ingested()

    for url in urls:
        print(f"Resolving: {url}")
        video_ids = get_video_ids(url)
        if not video_ids:
            print("  No videos found.\n")
            continue
        print(f"  Found {len(video_ids)} video(s)\n")

        for video_id in video_ids:
            raw_title  = get_video_title(video_id)
            title      = f"{cert}-{raw_title}"
            filename   = f"{title}.txt"
            srt_stem   = os.path.join(STUDY_DIR, title)
            srt_path   = srt_stem + ".en.srt"
            txt_path   = os.path.join(STUDY_DIR, filename)

            if filename in ingested:
                print(f"  [skip] {filename}")
                continue

            print(f"  Video: {raw_title}")
            print("  Downloading transcript...")
            download_srt(video_id, srt_stem)

            if not os.path.exists(srt_path):
                print("  No transcript — skipping\n")
                continue

            char_count = clean_srt(srt_path, txt_path)
            os.remove(srt_path)
            print(f"  Cleaned: {char_count} characters")

            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = chunk_text(text, title)
            print(f"  Chunks: {len(chunks)}")
            embed_and_upsert(chunks, cert, cert_label)

            ingested.add(filename)
            save_ingested(ingested)
            print(f"  Ingested as {cert_label}\n")

    print("Done.")

if __name__ == "__main__":
    main()
