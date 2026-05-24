# Prime Meridian 🧭

> AI-powered study tool for CompTIA certifications — built for learners, by a learner.

Prime Meridian is an open-source RAG (Retrieval-Augmented Generation) study assistant built to help you prep for CompTIA certifications like Security+, Linux+, Network+, CySA+, and PenTest+.

Ask it real questions. Get cited answers pulled directly from your study materials.

---

## Certifications Supported

- ✅ CompTIA Security+
- ✅ CompTIA Linux+
- 🔜 CompTIA Network+
- 🔜 CompTIA CySA+
- 🔜 CompTIA PenTest+

---

## How It Works

1. Study PDFs are chunked and embedded using OpenAI
2. Embeddings are stored in Pinecone
3. You ask a question in the UI
4. The most relevant chunks are retrieved and sent to Claude
5. Claude answers using only your study material — with citations

---

## Stack

| Layer | Tool |
|---|---|
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector DB | Pinecone (free tier) |
| LLM | Claude (Anthropic) |
| Frontend | Vanilla HTML/CSS/JS |
| Hosting | Cloudflare Pages |

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/prime-meridian.git
cd prime-meridian
```

### 2. Set up your environment

```bash
cp .env.example .env
# Fill in your API keys
```

### 3. Install dependencies

```bash
pip install -r ingest/requirements.txt
```

### 4. Add your study materials

Drop PDFs into `docs/study-materials/`. These are gitignored — your files stay local.

### 5. Ingest your documents

```bash
python ingest/ingest.py
```

### 6. Open the frontend

Open `frontend/index.html` in your browser or deploy to Cloudflare Pages.

---

## BYOK — Bring Your Own Keys

Prime Meridian is BYOK. You bring your own OpenAI and Anthropic API keys. They are never stored — only used in your browser session.

This keeps the tool free for everyone and puts you in control.

---

## Contributing

PRs welcome. If you add support for a new cert or improve the chunking logic, open a pull request.

---

## Disclaimer

This tool is for study purposes. All study materials used with this tool should be legally obtained. See `docs/study-materials/` for recommended free sources.

---

Built by [@YOUR_GITHUB](https://github.com/YOUR_GITHUB) · Powered by OpenAI + Anthropic + Pinecone
