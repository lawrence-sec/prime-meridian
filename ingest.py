# ingest.py
# Prime Meridian — PDF ingestion pipeline
# Chunks PDFs, embeds with OpenAI, stores in Pinecone

import os
import glob
from dotenv import load_dotenv

load_dotenv()

# TODO: implement chunking
# TODO: implement embedding
# TODO: implement Pinecone upsert

def main():
    print("Prime Meridian Ingestion Pipeline")
    print("-----------------------------------")
    pdf_files = glob.glob("../docs/study-materials/*.pdf")
    if not pdf_files:
        print("No PDFs found in docs/study-materials/")
        print("Add your study PDFs and run again.")
        return
    print(f"Found {len(pdf_files)} PDF(s):")
    for f in pdf_files:
        print(f"  - {f}")

if __name__ == "__main__":
    main()
