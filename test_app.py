import os
import sys
from fastapi.testclient import TestClient

# Add workspace directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.ragengine import GeminiRAGEngine
from backend.graph import create_research_graph
from backend.main import app

def test_rag_engine_init():
    print("Testing GeminiRAGEngine initialization...")
    engine = GeminiRAGEngine(upload_dir="./temp_docs")
    assert engine.upload_dir == "./temp_docs"
    assert len(engine.chunks) == 0
    print("OK: GeminiRAGEngine initialized successfully.")

def test_graph_compilation():
    print("Testing LangGraph agent graph compilation...")
    graph = create_research_graph()
    
    # Verify graph structure and nodes exist
    nodes = graph.get_graph().nodes
    print(f"Graph nodes found: {list(nodes.keys())}")
    
    assert "planner" in nodes
    assert "researcher" in nodes
    assert "writer" in nodes
    print("OK: LangGraph compiled and validated successfully.")

def test_api_endpoints():
    print("Testing FastAPI API router compilation...")
    client = TestClient(app)
    
    # 1. Test documents list endpoint
    res = client.get("/api/documents")
    assert res.status_code == 200
    print(f"OK: Documents list endpoint returned: {res.json()}")
    
    # 2. Test briefings list endpoint
    res = client.get("/api/briefings")
    assert res.status_code == 200
    print(f"OK: Briefings history list endpoint returned: {res.json()}")
    
    # 3. Test research post endpoint returns validation errors on missing fields
    res = client.post("/api/research", json={"topic": ""})
    assert res.status_code == 400
    print("OK: Research input validation checks function correctly.")
    
    print("OK: FastAPI endpoints tested and verified.")

if __name__ == "__main__":
    print("Running verification suite...")
    test_rag_engine_init()
    print("-" * 40)
    test_graph_compilation()
    print("-" * 40)
    test_api_endpoints()
    print("-" * 40)
    print("CONGRATULATIONS! Codebase compilation and routing tests completed successfully.")
