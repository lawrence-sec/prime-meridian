# rename_files.py
# Prime Meridian — Auto cert tagger via filename parsing
# Detects cert from filename, renames with proper prefix
# Updates ingested.json to match new filenames

import os
import re
import json

STUDY_DIR    = "study-materials"
INGESTED_LOG = "ingested.json"

# Detection patterns — order matters, more specific first
CERT_PATTERNS = [
    ("cysa-plus",    r"cysa|cs0-00[23]|cybersecurity.?analyst"),
    ("pentest-plus", r"pentest|pt0-00[23]|pen.?test"),
    ("linux-plus",   r"linux|xk0-00[45]"),
    ("network-plus", r"network|n10-00[789]"),
    ("security-plus",r"security|sy0-[567]0[12]"),
]

def detect_cert(filename):
    lower = filename.lower()
    for cert, pattern in CERT_PATTERNS:
        if re.search(pattern, lower):
            return cert
    return None

def load_ingested():
    if os.path.exists(INGESTED_LOG):
        with open(INGESTED_LOG) as f:
            return json.load(f)
    return []

def save_ingested(data):
    with open(INGESTED_LOG, "w") as f:
        json.dump(data, f, indent=2)

def main():
    print("=================================")
    print("  Prime Meridian — File Renamer")
    print("=================================\n")

    files    = os.listdir(STUDY_DIR)
    ingested = load_ingested()

    renames  = []
    skipped  = []
    unknown  = []

    for filename in sorted(files):
        if not (filename.endswith(".txt") or filename.endswith(".pdf")):
            continue

        cert = detect_cert(filename)
        ext  = os.path.splitext(filename)[1]
        base = os.path.splitext(filename)[0]

        if cert and not filename.startswith(cert):
            # Strip any existing cert prefix to avoid double-prefixing
            clean = base
            for c in [c for c,_ in CERT_PATTERNS]:
                clean = re.sub(f'^{c}-?', '', clean)
            new_name = f"{cert}-{clean.lstrip('-')}{ext}"
            renames.append((filename, new_name, cert))
        elif cert and filename.startswith(cert):
            skipped.append((filename, cert))
        else:
            unknown.append(filename)

    # Preview
    print(f"Files to rename: {len(renames)}")
    print(f"Already correct: {len(skipped)}")
    print(f"Cannot detect:   {len(unknown)}\n")

    if renames:
        print("Preview (first 20):")
        for old, new, cert in renames[:20]:
            print(f"  [{cert}] {old[:50]}")
            print(f"        -> {new[:50]}")
        if len(renames) > 20:
            print(f"  ... and {len(renames)-20} more\n")

    if unknown:
        print("\nCould not detect cert for:")
        for f in unknown:
            print(f"  {f}")

    print()
    confirm = input(f"Rename {len(renames)} files? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    # Rename files and update ingested.json
    renamed_count = 0
    for old, new, cert in renames:
        old_path = os.path.join(STUDY_DIR, old)
        new_path = os.path.join(STUDY_DIR, new)

        try:
            os.rename(old_path, new_path)

            # Update ingested.json
            if old in ingested:
                ingested[ingested.index(old)] = new

            renamed_count += 1
        except Exception as e:
            print(f"  Error renaming {old}: {e}")

    save_ingested(ingested)

    print(f"\nDone. Renamed {renamed_count} files.")
    print("ingested.json updated.")
    print("\nNext: run tag_certs.py to update Pinecone metadata.")

if __name__ == "__main__":
    main()
