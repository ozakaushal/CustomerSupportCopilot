import time
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from app.core.config import get_settings

settings = get_settings()

# size of the vector for each huggingface embedding model
EMBEDDING_DIMS = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
}

vector_store = None


# connects to pinecone and creates the index if it doesn't exist
def get_index():
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is missing in .env")

    dims = EMBEDDING_DIMS.get(settings.embedding_model)
    if dims is None:
        raise ValueError("Add dimension for " + settings.embedding_model + " in EMBEDDING_DIMS")

    pc = Pinecone(api_key=settings.pinecone_api_key)
    index_name = settings.vector_index

    if not pc.has_index(index_name):
        pc.create_index(
            name=index_name,
            dimension=dims,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # wait till the index is ready
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)
    elif pc.describe_index(index_name).dimension != dims:
        raise RuntimeError("Index dimension does not match embedding model, use a new VECTOR_INDEX name")

    return pc.Index(index_name)


# returns the pinecone vector store, creates it only once
def get_vector_store():
    global vector_store
    if vector_store is None:
        # model runs locally, hf token is only used to download it the first time
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu", "token": settings.hf_token or None},
            encode_kwargs={"normalize_embeddings": True},
        )
        vector_store = PineconeVectorStore(
            index=get_index(),
            embedding=embeddings,
            namespace=settings.vector_namespace,
        )
    return vector_store


# finds the chunks most similar to the query
def search(query):
    return get_vector_store().similarity_search(query, k=settings.retrieval_k)


# stores new chunks in pinecone and returns their ids
def index_chunks(chunks):
    return get_vector_store().add_documents(chunks)
