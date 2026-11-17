import os
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from backend.api.core import UPLOAD_DIR, datetime, rag_engine

router = APIRouter()

@router.get("/api/documents")
def list_documents():
    """Lists files uploaded for search index."""
    files = []
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            filepath = os.path.join(UPLOAD_DIR, filename)
            # Skip hidden directory/files like .cache and chroma_db
            if filename.startswith(".") or filename == "chroma_db":
                continue
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    "name": filename,
                    "size": stat.st_size,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
    return files

@router.post("/api/documents/upload")
async def upload_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """Receives and writes files into the upload folder, then indexes in the background."""
    uploaded = []
    for file in files:
        filename = os.path.basename(file.filename)
        filepath = os.path.join(UPLOAD_DIR, filename)
        try:
            with open(filepath, "wb") as f:
                content = await file.read()
                f.write(content)
            uploaded.append(filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {filename}: {e}")
            
    # Trigger RAG Indexing in the background immediately
    api_key = os.getenv("GEMINI_API_KEY", "")
    rag_engine.indexing_logs = ["Initializing indexing queue..."]
    rag_engine.is_indexing = True
    background_tasks.add_task(rag_engine.load_and_index, api_key)
    
    return {"message": "Files uploaded successfully", "files": uploaded}

@router.delete("/api/documents/{filename}")
def delete_document(filename: str):
    """Deletes files from upload folder and cleans up related database entries and cache files."""
    filename = os.path.basename(filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            
            # Delete entries from ChromaDB
            try:
                rag_engine.collection.delete(where={"source": filename})
            except Exception as e:
                print(f"Warning: Failed to delete database entries for {filename} from ChromaDB: {e}")
            
            # Clean up transcribed PDF text in cache directory
            txt_cache = os.path.join(UPLOAD_DIR, ".cache", f"{filename}.txt")
            if os.path.exists(txt_cache):
                try:
                    os.remove(txt_cache)
                except Exception as e:
                    pass
                    
            # Clean up legacy cache files if any
            legacy_cache = os.path.join(UPLOAD_DIR, ".cache", f"{filename}.embeddings.json")
            if os.path.exists(legacy_cache):
                try:
                    os.remove(legacy_cache)
                except Exception as e:
                    pass

            return {"message": f"Deleted {filename} and associated database/cache files."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete {filename}: {e}")
    else:
        raise HTTPException(status_code=404, detail="File not found")

@router.get("/api/documents/indexing-status")
def get_indexing_status():
    """Returns the background indexing status and logs of the RAG engine."""
    return {
        "is_indexing": rag_engine.is_indexing,
        "logs": rag_engine.indexing_logs
    }
