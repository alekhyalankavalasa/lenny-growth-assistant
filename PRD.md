# PRD — The Lenny Growth Assistant

> **Document type**: Forward-Deployment Discovery Brief + Product Requirements  
> **Status**: Living document — updated as assumptions resolve  
> **Last updated**: Phase 1 Scaffold

---

## 1. User and Problem

**Primary user**: A product manager or growth practitioner at a company using Lenny's Podcast/Newsletter as a reference for product strategy, hiring, retention, and growth frameworks.

**Job to be done**:  
*"When I have a product question, I want a grounded, citable answer drawn from Lenny's content — not a hallucinated synthesis — and I want to turn that answer into a polished, shareable essay without copy-pasting into a writing tool."*

**Pain removed**:
- Scrubbing through 5+ hours of podcast audio to verify a claim
- Getting generic ChatGPT answers that cite no source
- Re-formatting raw notes into publishable content manually
- Context loss between chat sessions

---

## 2. Success Metric

**Primary**: ≥ 80% of grounded-QA answers include at least one source citation traceable to a specific transcript chunk.

**Secondary operational**:
- Cold startup (docker compose up) → all services healthy within 90 seconds
- P95 response latency ≤ 15 seconds (cloud) / ≤ 45 seconds (local Ollama)
- Zero unhandled 5xx crashes across the 5 documented failure modes

---

## 3. Assumptions

| # | Assumption | Why assumed | How to override |
|---|---|---|---|
| A1 | Transcript corpus = free public GitHub starter pack (~50 podcast + 10 newsletter MDs) | Full corpus requires paid lennysdata.com sub; starter pack is sufficient for demo | Provide path to full corpus or paid credentials |
| A2 | Local Ollama model = `llama3.2` (4-bit, ~4 GB) | Runs on typical 8GB dev machine | Set `OLLAMA_MODEL` in `.env` |
| A3 | Embedding model = `text-embedding-3-small` (cloud) / `nomic-embed-text` (Ollama) | Best size/quality tradeoff for each mode | Set `EMBEDDING_MODEL` / `OLLAMA_EMBEDDING_MODEL` in `.env` |
| A4 | Ship 30 for 30 output = ~1,250-word long-form newsletter essay following Ship 30 principles | Brief specified 1,250 words; original Ship 30 essays are 250 words (atomic); interpreted as "newsletter length with Ship 30 structure" | Adjust `TARGET_WORD_COUNT` in skill config |
| A5 | Frontend = React + Vite | Workspace convention; brief did not specify | Can migrate to Next.js post-handoff |
| A6 | No user authentication | Demo context; sessions are anonymous UUID-keyed | Add Auth0/Supabase Auth in post-demo hardening |
| A7 | GitHub repo = local folder; user creates remote and pushes | Agent cannot create remote GitHub repos | User runs `git init && git remote add origin ...` |
| A8 | Demo video = shooting script only | No video tooling available to agent | User records 2-3 min video using the script |
| A9 | HTML artifact sandbox = `allow-same-origin` only, no scripts | Defense-first security posture | Documented in architecture.md |
| A10 | pgvector dimension = 1536 for OpenAI embeddings; 768 for nomic-embed-text | Fixed by embedding model choice | Both stored in same table with dimension-aware column |

---

## 4. Scope

### In scope
- Chat interface with session isolation (new session = fresh context)
- Grounded Q&A skill with source citation (transcript chunks)
- Ship 30 for 30 essay generation skill (~1,250 words, grounded)
- In-app Artifact Viewer (rendered Markdown + sandboxed HTML)
- Switchable LLM providers: Anthropic Claude, OpenAI, Ollama (local)
- Provider indicator visible in UI
- One-command Docker Compose startup
- PostgreSQL + pgvector for persistence + vector search
- Automated test suite + manual UI test plan
- Full documentation set (README, PRD, architecture, design)

### Deliberately out of scope (and why)
- User authentication/accounts — adds significant complexity for a demo
- Full Lenny corpus (370+ transcripts) — starter pack is sufficient for grounding demo
- Real-time transcript ingestion / RSS polling — static ingestion is sufficient
- Mobile-native app — responsive web is sufficient
- Speech-to-text query input — out of scope for PM/growth practitioner persona
- Fine-tuning — RAG is sufficient and cheaper for a demo knowledge base

---

## 5. User Flows

### Flow 1: Grounded Q&A
1. User opens app → lands on new empty session
2. Types question: *"What does Lenny say about how Duolingo grew its DAU?"*
3. Agent retrieves relevant transcript chunks → generates answer with citations
4. User asks follow-up → prior context preserved in session
5. User can see source episode names inline with answer

### Flow 2: Ship 30 Essay Generation
1. User types: *"Write a Ship 30 essay about Lenny's retention framework"*
2. Agent routes to Ship 30 skill → retrieves grounding material → generates ~1,250-word essay
3. Artifact Viewer panel opens beside chat with rendered essay
4. User copies or downloads the essay

### Flow 3: Provider Toggle
1. User (or operator) edits `.env`: `LLM_PROVIDER=anthropic`
2. Restarts backend: `docker compose restart backend`
3. Provider indicator in UI updates to show "Claude claude-sonnet-4-5"
4. All subsequent requests use Anthropic API

### Flow 4: Failure Graceful Handling
1. Ollama service is not running
2. User sends a message
3. Backend detects Ollama unavailable, returns 503 with message: *"Local model (Ollama) is not reachable. Start Ollama or set LLM_PROVIDER=anthropic in .env."*
4. UI shows dismissible error banner, no crash

---

## 6. Acceptance Criteria

| ID | Criteria | Testable? |
|---|---|---|
| AC1 | Fresh clone + documented steps → full stack in one command | Yes — Phase 10 |
| AC2 | New chat creates isolated session; follow-ups preserve context | Yes — automated |
| AC3 | Answers cite specific transcript source(s) | Yes — automated |
| AC4 | When retrieval empty, agent admits it rather than guessing | Yes — automated |
| AC5 | Ship 30 skill is a distinct bounded skill (not ad-hoc prompt) | Yes — code review |
| AC6 | Essay output ≥ 1,100 words (within 10% of 1,250 target) | Yes — automated |
| AC7 | Artifact Viewer renders beside chat; HTML `<script>` stripped | Yes — automated + manual |
| AC8 | LLM provider switchable via `.env` only, visible in UI | Yes — manual |
| AC9 | All 5 failure modes fail gracefully with documented log messages | Yes — Phase 7 resilience |
| AC10 | No secrets in repo; `.env.example` complete and accurate | Yes — code review |
| AC11 | All 8 deliverables exist and are internally consistent | Yes — Phase 9 docs |

---

## 7. Risks and Trade-offs

| Risk | Severity | Mitigation | Accepted? |
|---|---|---|---|
| **Hallucination**: Model answers beyond knowledge base | High | Strict grounding prompt + "I don't know" path when retrieval returns empty | Mitigated |
| **Local LLM quality gap**: Ollama answers lower quality than Claude | Medium | Documented prominently; demo defaults to local but README recommends cloud for production | Accepted |
| **HTML artifact XSS**: User-supplied or model-generated HTML runs scripts | High | Server-side `bleach` sanitizer + client `DOMPurify` + `sandbox` iframe (no scripts) | Mitigated |
| **Latency**: Local model slow on CPU | Medium | Streaming output + 60s timeout + loading states + retry button | Accepted |
| **Transcript IP**: Redistributing Lenny's content | Medium | Only public starter pack; ingested locally, not committed to repo; README instructs user to ingest their own corpus | Mitigated |
| **DB connection failure**: Postgres unreachable | Medium | 503 graceful degradation, retry logic, clear health endpoint | Mitigated |
| **Ollama cold start**: First model load takes 30-60s | Low | Health check waits; UI shows "model loading" state | Mitigated |
| **Embedding dimension mismatch**: Switching models changes vector dimension | Medium | Separate embedding config; ingest script warns if dimension changes from existing data | Accepted (documented) |
| **Cost bleed**: Cloud embeddings at scale | Low | Starter pack is ~60 docs; negligible cost; local embedding option documented | Accepted |

---

## 8. Implementation Plan Reference

See [implementation_plan.md](implementation_plan.md) for the full 10-phase build plan with subtasks and verification steps.
