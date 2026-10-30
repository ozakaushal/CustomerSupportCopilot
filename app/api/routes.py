import logging
from pathlib import Path
from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from app.core.config import get_settings
from app.rag.graph import run_copilot
from app.rag.knowledge_base import index_chunks
from app.services.chat_log import log_chat, recent_chats
from app.services.documents import ALLOWED_EXTENSIONS, load_document, split_documents

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    question: str


# stops the request if the ingest token is not set or is wrong
def check_token(token):
    if not settings.ingest_token:
        raise HTTPException(status_code=503, detail="INGEST_TOKEN is not set on the server")
    if token != settings.ingest_token:
        raise HTTPException(status_code=401, detail="Wrong ingest token")


# simple health check to see if the app is running
@router.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# takes a question from the UI and returns the copilot answer
@router.post("/chat")
def chat(request: ChatRequest):
    question = request.question.strip()
    if len(question) < 2:
        raise HTTPException(status_code=400, detail="Question is too short")

    try:
        result = run_copilot(question)
    except Exception as e:
        logger.exception("Error while running copilot")
        raise HTTPException(status_code=500, detail=str(e))

    log_chat(question, result["answered_by"], result["steps"])

    return {
        "answer": result["answer"],
        "answered_by": result["answered_by"],
        "steps": result["steps"],
        "sources": result["sources"],
        "search_query": result["search_query"],
    }


# uploads a new document, saves it and adds it to pinecone
@router.post("/documents")
def upload_document(file: UploadFile = File(...), x_ingest_token: str = Header(default="")):
    check_token(x_ingest_token)

    file_name = Path(file.filename).name
    ext = Path(file_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only pdf, docx, md and txt files are allowed")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / file_name
    with open(save_path, "wb") as f:
        f.write(file.file.read())

    docs = load_document(save_path)
    chunks = split_documents(docs)
    ids = index_chunks(chunks)

    return {"file": file_name, "chunks": len(chunks), "vectors": len(ids)}


# returns the last few questions asked to the copilot
@router.get("/history")
def history(limit: int = 20, x_ingest_token: str = Header(default="")):
    check_token(x_ingest_token)
    if limit > 100:
        limit = 100
    return recent_chats(limit)
