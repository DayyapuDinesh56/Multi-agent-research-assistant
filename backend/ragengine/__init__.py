import os
import chromadb
from typing import List, Any
from sentence_transformers import SentenceTransformer
from backend.ragengine.indexer import DocumentChunk, load_and_index
from backend.ragengine.searcher import search

class GeminiRAGEngine:
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        self.chunks: List[DocumentChunk] = []
        # Set download timeout to 120s to prevent ReadTimeout on slow networks
        os.environ["HF_HUB_HTTP_TIMEOUT"] = "120"
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize local persistent ChromaDB client
        chroma_dir = os.path.join(self.upload_dir, "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=chroma_dir)
        self.collection = self.chroma_client.get_or_create_collection(name="research_assistant")
        
        # State tracking for real-time background indexing logs
        self.is_indexing = False
        self.indexing_logs: List[str] = []

    def load_and_index(self, api_key: str, log_callback: Any = None):
        self.is_indexing = True
        self.indexing_logs = ["RAG: Starting background indexing process..."]
        
        def wrapper_callback(msg):
            self.indexing_logs.append(msg)
            if log_callback:
                log_callback(msg)
            else:
                print(msg)
                
        try:
            return load_and_index(self, api_key, wrapper_callback)
        except Exception as e:
            import traceback
            err_msg = f"RAG Crash: Background indexing failed: {e}\n{traceback.format_exc()}"
            wrapper_callback(err_msg)
            raise e
        finally:
            self.is_indexing = False

    def search(self, api_key: str, query: str, top_k: int = 3) -> List[dict]:
        return search(self, api_key, query, top_k)
