# The Lenny Growth Assistant

An AI-powered conversational web application acting as a growth assistant, grounded strictly in Lenny's Podcast and Newsletter content. It provides expert Q&A and can draft full-length Ship 30 essays using RAG (Retrieval-Augmented Generation).

## Features

- **Full-stack AI Architecture:** FastAPI backend, React + Vite frontend, PostgreSQL (`pgvector`) database.
- **RAG + Hybrid Search:** Uses pgvector cosine similarity and full-text `tsvector` with Reciprocal Rank Fusion (RRF) and Maximal Marginal Relevance (MMR) deduplication to ensure diverse, high-relevance context.
- **LLM Agnostic:** Switch between cloud models (Anthropic, OpenAI) and local, privacy-preserving models (Ollama) by modifying `.env` only. Implements the Strategy Pattern for seamless fallback.
- **Bounded Agent Skills:** The assistant strictly routes messages to specific skills (`grounded_qa` or `ship30_essay`) to prevent prompt drift and enforce formatting.
- **Artifact Generation & Viewer:** Generates markdown/HTML essays which are securely rendered in a side-by-side Artifact Viewer panel. Uses `bleach` server-side and `DOMPurify` + sandboxed `iframes` client-side for defense-in-depth sanitization.
- **SSE Streaming:** Real-time token streaming and asynchronous source fetching.
- **Automated Ingestion:** Python script to automatically fetch the public Lenny transcript repository, parse markdown frontmatter, intelligently chunk, embed, and idempotently upsert to pgvector.

---

## 🚀 Quick Start (One-Command Setup)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed.

### 1. Setup Environment
```bash
git clone <repository_url> lenny-growth-assistant
cd lenny-growth-assistant

# Create environment file from template
cp .env.example .env
```
Open `.env` and:
- Select your `LLM_PROVIDER` (`ollama`, `anthropic`, or `openai`).
- Add your API keys if using cloud providers.

### 2. Start the Stack
Start the entire stack (Database, Backend, Frontend, and Ollama if enabled).
```bash
docker compose up -d
```
*(On first start, the database will initialize and Ollama will automatically pull the required models if you are running locally).*

### 3. Ingest Transcripts (First time only)
Run the ingestion pipeline to fetch transcripts from GitHub, chunk them, embed them, and save them to the database.
```bash
docker compose run --rm ingest
```

### 4. Access the App
- **Frontend:** http://localhost:5173
- **Backend API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health/ready

---

## Architecture

Please see `architecture.md` for a detailed breakdown of the technical decisions, RAG pipeline, and security implementations.

## Design

The UI is built with a custom CSS design system leveraging dark glassmorphism, HSL color palettes, and modern typography (Inter/JetBrains Mono).
See `design.md` for UI/UX principles, information architecture, and accessibility considerations.

## Manual UI Test Plan

To manually verify the UI functionality, perform the following steps:
1. **Fresh Session**: Start the app and ensure the "New Chat" button creates a fresh empty state.
2. **Standard Q&A**: Ask "What does Lenny say about Duolingo?". Verify the streaming text, check that the answer includes a source citation (pill/link), and verify that the LLM provider indicator correctly displays the active model.
3. **Artifact Generation**: Ask "Write a Ship 30 essay about retention". Wait for the generation. Verify that the Artifact Viewer side panel automatically slides in and renders the essay formatting correctly.
4. **Resilience Test**: Stop the Ollama container (`docker compose stop ollama`). Send a message. Verify that a red error banner gracefully catches the 503 error without crashing the UI, instructing you to check the local model.

## Development

If you wish to run the app outside of Docker:
1. Start Postgres: `docker compose up db -d`
2. Backend: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
3. Frontend: `cd frontend && npm install && npm run dev`

## image 
<img width="2932" height="1666" alt="WhatsApp Image 2026-09-16 at 00 57 23" src="https://github.com/user-attachments/assets/f22c3155-35a6-4e85-9de3-becc47e27c20" />
<img width="2940" height="1664" alt="WhatsApp Image 2026-09-16 at 00 57 45" src="https://github.com/user-attachments/assets/b0b04b43-fd33-437e-9bd6-31371a5c40e5" />
<img width="2936" height="1664" alt="WhatsApp Image 2026-09-16 at 00 57 09" src="https://github.com/user-attachments/assets/121ee992-75a9-46e6-b3e6-9e772e19ff17" />


