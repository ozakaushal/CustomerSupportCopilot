# Customer Support Copilot

A support assistant for the IT service desk at **Atharva ITS**. Employees ask questions in plain
English ("how do I connect to the VPN?", "what do I do if my laptop is stolen?") and get an answer
from the company's own IT documents. If the documents don't cover it, the copilot falls back to
a web search and says clearly that the answer came from outside.

Built with LangGraph, FastAPI, Groq, HuggingFace embeddings, Pinecone and Tavily. The frontend is plain HTML/CSS/JS.

## Why

The service desk gets the same tickets over and over: VPN problems, password resets, MFA,
software requests. The answers are already written down, but people can't find them, and a
generic chatbot will happily make up a company policy. The goal here is:

- answer from internal docs first and show which document was used
- only go to the web when the internal docs really don't have it
- say "I don't know, raise a ticket" instead of guessing
- let the IT team add new documents without touching code
- keep a log of what was asked and how it was answered

## How it works

Every question goes through a LangGraph flow:

```
question
   |
classify ----------------------------> small talk reply
   | (IT question)
search knowledge base (Pinecone)
   |
good enough? -- yes --> answer from knowledge base
   | no
search web (Tavily)
   |
good enough? -- yes --> answer from web (with a warning)
   | no
rewrite the query and try again (MAX_REWRITES times)
   |
still nothing --> "please raise a ticket"
```

The "good enough?" step asks the LLM to check the search results before writing the answer.
Normal RAG just answers with whatever it found, even if the results are not related.

The right side panel in the UI shows all the steps, so you can see why a question went to the
web instead of the knowledge base.

## Project layout

```
app/
  api/routes.py            chat, document upload, health and history endpoints
  core/config.py           settings loaded from .env
  core/telemetry.py        logging setup
  rag/state.py             data passed between graph steps
  rag/prompts.py           all LLM prompts in one place
  rag/knowledge_base.py    Pinecone index + HuggingFace embeddings
  rag/graph.py             the LangGraph workflow
  services/documents.py    loading and chunking PDF / DOCX / MD / TXT
  services/chat_log.py     SQLite log of questions and steps
  main.py                  FastAPI app
data/knowledge/            sample Atharva ITS policies and service desk playbook
static/, templates/        frontend
ingest_sample_kb.py        loads data/knowledge into Pinecone
run.py                     starts the dev server
```

## Running it locally

Needs Python 3.11+ and API keys for Groq, Pinecone, Tavily and a HuggingFace token (all have free tiers).
The embedding model runs locally on CPU, the HF token is only used to download it the first time
(about 90 MB, so the first run takes a minute or two).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
cp .env.example .env            # then fill in the keys
```

Load the sample documents (this creates the Pinecone index on the first run):

```bash
python ingest_sample_kb.py
```

Start the app:

```bash
python run.py
```

Open http://127.0.0.1:8000. API docs are at http://127.0.0.1:8000/docs.

### Environment variables

| Name | Default | Notes |
| ---- | ------- | ----- |
| `GROQ_API_KEY` | | chat model |
| `HF_TOKEN` | | downloads the embedding model |
| `TAVILY_API_KEY` | | web search fallback |
| `PINECONE_API_KEY` | | vector store |
| `CHAT_MODEL` | `qwen/qwen3.8-27b` | any Groq chat model, `openai/gpt-oss-120b` also works well |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | must be listed in `EMBEDDING_DIMS` in `knowledge_base.py` |
| `VECTOR_INDEX` | `it-support` | created automatically if missing |
| `VECTOR_NAMESPACE` | `company_private_kb` | |
| `RETRIEVAL_K` | `4` | chunks pulled per search |
| `MAX_REWRITES` | `1` | how many times to rewrite the query before giving up |
| `INGEST_TOKEN` | | required for `/api/documents` and `/api/history`, both are disabled if empty |
| `ENVIRONMENT` | `development` | |

If you change `EMBEDDING_MODEL` to one with a different dimension, also change `VECTOR_INDEX`.
The app won't overwrite an existing index with a different dimension.

### Docker

```bash
docker build -t support-copilot .
docker run --env-file .env -p 8000:8000 support-copilot
```

## API

`POST /api/chat`

```json
{ "question": "How do I reset my password?" }
```

```json
{
  "answer": "...",
  "answered_by": "knowledge_base",
  "steps": [
    "Classified as: kb",
    "Knowledge base search: 4 chunks found",
    "Knowledge base results: enough",
    "Answered from knowledge base"
  ],
  "sources": [{ "title": "it_policies.md", "url": "", "kind": "kb" }],
  "search_query": "How do I reset my password?"
}
```

`answered_by` is one of `knowledge_base`, `web`, `chat` or `none`.

`POST /api/documents` takes a multipart file upload with an `X-Ingest-Token` header. The file is
chunked, embedded and searchable right away.

`GET /api/history?limit=20` returns the latest logged questions (same header).

`GET /api/health` is a basic health check.

## Things to try

| Question | Expected path |
| -------- | ------------- |
| How do I connect to the VPN from home? | knowledge base |
| Will the service desk ever ask for my MFA code? | knowledge base |
| What is the response time for a P2 ticket? | knowledge base |
| Is Microsoft Teams having an outage today? | knowledge base not enough, then web |
| My chat app is acting weird since the update | may rewrite the query and retry |
| hi there | small talk, no search |

## Not done yet

- no login, anyone who can reach the app can ask questions
- uploads with the same file name overwrite the saved file but add new vectors (no dedupe)
- no tests for the graph yet, only manual checks
