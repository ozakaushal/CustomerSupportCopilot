from pathlib import Path
from app.core.config import get_settings
from app.rag.knowledge_base import index_chunks
from app.services.documents import ALLOWED_EXTENSIONS, load_document, split_documents


# loads all files from data/knowledge and uploads them to pinecone
def main():
    folder = Path(get_settings().knowledge_dir)

    all_docs = []
    file_count = 0
    for path in folder.iterdir():
        if path.suffix.lower() in ALLOWED_EXTENSIONS:
            print("Loading", path.name)
            all_docs.extend(load_document(path))
            file_count += 1

    if file_count == 0:
        print("No files found in", folder)
        return

    chunks = split_documents(all_docs)
    ids = index_chunks(chunks)
    print(f"Done: {file_count} files, {len(chunks)} chunks, {len(ids)} vectors")


if __name__ == "__main__":
    main()
