import numpy as np
from typing import List, Dict, Any

def search(self, api_key: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Searches the indexed chunks using ChromaDB query."""
    try:
        query_vector = np.array(self.model.encode(query), dtype=np.float32).tolist()
    except Exception as e:
        print(f"RAG Error: Failed to generate query embedding: {e}")
        return []

    try:
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )
    except Exception as e:
        print(f"RAG Error: ChromaDB query failed: {e}")
        return []

    formatted_results = []
    
    if not results or "documents" not in results or not results["documents"]:
        return []
        
    documents = results["documents"][0]
    metadatas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else []
    distances = results["distances"][0] if "distances" in results and results["distances"] else []

    for idx, doc in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else 0.0
        
        # Convert distance to similarity score
        score = 1.0 - float(distance) if distance is not None else 0.5
        
        formatted_results.append({
            "text": doc,
            "source": metadata.get("source", "Unknown"),
            "page": metadata.get("page", -1),
            "score": score
        })
        
    return formatted_results
