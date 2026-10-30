from docx import Document as DocxFile
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".docx"]


# reads a pdf / txt / md / docx file and returns it as langchain documents
def load_document(path):
    ext = path.suffix.lower()

    if ext == ".pdf":
        docs = PyPDFLoader(str(path)).load()
    elif ext == ".txt" or ext == ".md":
        docs = TextLoader(str(path), encoding="utf-8").load()
    elif ext == ".docx":
        word_file = DocxFile(str(path))
        text = ""
        for para in word_file.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
        docs = [Document(page_content=text)]
    else:
        raise ValueError("File type not allowed: " + ext)

    # save only file name as source, not the full path
    for doc in docs:
        doc.metadata["source"] = path.name

    return docs


# breaks the documents into smaller chunks so they can be stored in pinecone
def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    return splitter.split_documents(docs)
