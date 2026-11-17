import os
import uuid
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.ragengine import GeminiRAGEngine
from backend.graph import create_research_graph

# Load environment configuration
load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "documents")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Instances
rag_engine = GeminiRAGEngine(upload_dir=UPLOAD_DIR)
workflow_graph = create_research_graph()

class TaskState:
    def __init__(self, task_id: str, topic: str):
        self.task_id = task_id
        self.topic = topic
        self.status = "pending"
        self.plan = []
        self.findings = {}
        self.report = ""
        self.logs = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

# Store active task states in memory
active_tasks: Dict[str, TaskState] = {}

class ResearchRequest(BaseModel):
    topic: str
    api_key: Optional[str] = None

def run_agent_workflow(task_id: str, topic: str, api_key: str):
    """Worker task executing inside a background thread pool."""
    task = active_tasks[task_id]
    
    def log_cb(log_entry):
        task.logs.append(log_entry)
        task.updated_at = datetime.now().isoformat()

    try:
        # Run LangGraph agent orchestrator directly
        task.status = "planning"
        log_cb({"timestamp": datetime.now().isoformat(), "agent": "Planner", "message": "Starting research query orchestration..."})
        initial_state = {
            "topic": topic,
            "api_key": api_key,
            "plan": [],
            "findings": {},
            "report": "",
            "logs": task.logs,
            "status": "planning"
        }
        
        config = {
            "configurable": {
                "rag_engine": rag_engine,
                "log_callback": log_cb
            }
        }
        
        # Synchronously invoke graph inside background worker thread
        final_state = workflow_graph.invoke(initial_state, config)
        
        task.plan = final_state.get("plan", [])
        task.findings = final_state.get("findings", {})
        task.report = final_state.get("report", "")
        task.status = final_state.get("status", "completed")
        
        # Save output briefing markdown
        if task.status == "completed" and task.report:
            safe_topic = "".join([c if c.isalnum() else "_" for c in topic[:40]])
            filename = f"briefing_{safe_topic}_{task_id[:8]}.md"
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(task.report)
            log_cb({"timestamp": datetime.now().isoformat(), "agent": "System", "message": f"System: Final research report saved as {filename}"})
            
    except Exception as e:
        task.status = "failed"
        log_cb({"timestamp": datetime.now().isoformat(), "agent": "System", "message": f"System Error during orchestration: {str(e)}"})
