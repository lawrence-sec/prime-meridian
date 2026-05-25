# tag_certs.py
# Prime Meridian — Auto cert tagger
# Reads cert from filename prefix, updates Pinecone metadata in bulk

import os
import json
from dotenv import load_dotenv
from pinecone import Pinecone
from tqdm import tqdm

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST    = os.getenv("PINECONE_HOST")
INGESTED_LOG     = "ingested.json"

pc    = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(host=PINECONE_HOST)

CERT_PREFIXES = {
    "security-plus": "Security+",
    "network-plus":  "Network+",
    "linux-plus":    "Linux+",
    "cysa-plus":     "CySA+",
    "pentest-plus":  "PenTest+"
}

def detect_cert(filename):
    for prefix, label in CERT_PREFIXES.items():
        if filename.lower().startswith(prefix):
            return prefix, label
    return None, None

def load_ingested():
    if not os.path.exists(INGESTED_LOG):
        print("No ingested.json found.")
        return []
    with open(INGESTED_LOG) as f:
        return json.load(f)

def get_source(filename):
    return os.path.splitext(filename)[0]

def update_vectors(source, cert, cert_label):
    dummy_vec = [0.0] * 512
    results   = index.query(
        vector=dummy_vec,
        top_k=1000,
        filter={"source": {"$eq": source}},
        include_metadata=True,
        include_values=True
    )
    

    if not results.matches:
        return 0

    vectors = []
    for match in results.matches:
        meta = dict(match.metadata)
        meta["cert"]       = cert
        meta["cert_label"] = cert_label
        vectors.append({
            "id":       match.id,
            "values":   match.values,
            "metadata": meta
        })

    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i:i+100])

    return len(vectors)

def main():
    print("=================================")
    print("  Prime Meridian — Auto Cert Tagger")
    print("=================================\n")

    files = load_ingested()
    if not files:
        print("Nothing in ingested.json.")
        return

    detected  = []
    undetected = []

    for f in files:
        cert, label = detect_cert(f)
        if cert:
            detected.append((f, cert, label))
        else:
            undetected.append(f)

    print(f"Auto-detected: {len(detected)} files")
    print(f"Unknown cert:  {len(undetected)} files\n")

    if undetected:
        print("Could not detect cert for:")
        for f in undetected:
            print(f"  {f}")
        print()

    confirm = input(f"Tag {len(detected)} files in Pinecone? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    print()
    total_updated = 0
    for filename, cert, label in tqdm(detected, desc="Tagging"):
        source  = get_source(filename)
        updated = update_vectors(source, cert, label)
        total_updated += updated

    print(f"\nDone. Updated {total_updated} vectors across {len(detected)} sources.")
    print("Quiz cert filtering will now work in the frontend.")

if __name__ == "__main__":
    main()
