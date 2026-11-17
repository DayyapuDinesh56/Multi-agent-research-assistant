import uuid
import json
import asyncio
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from backend.api.core import active_tasks, TaskState, ResearchRequest, run_agent_workflow

router = APIRouter()

@router.post("/api/research")
def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Initiates the research graph background task."""
    api_key = request.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="Gemini API Key is required. Set GEMINI_API_KEY environment variable, create a .env file, or submit the key in the request."
        )
        
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Research topic cannot be empty.")

    task_id = str(uuid.uuid4())
    active_tasks[task_id] = TaskState(task_id, request.topic)
    
    background_tasks.add_task(run_agent_workflow, task_id, request.topic, api_key)
    
    return {"task_id": task_id, "status": "started"}

@router.get("/api/research/stream/{task_id}")
async def stream_task_logs(task_id: str):
    """Streams running agent log entries as Server-Sent Events (SSE)."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    async def event_generator():
        client_index = 0
        while True:
            task = active_tasks[task_id]
            logs = task.logs
            
            # Flush new log entries to client
            if client_index < len(logs):
                for i in range(client_index, len(logs)):
                    yield f"data: {json.dumps(logs[i])}\n\n"
                client_index = len(logs)
                
            # If task has completed, yield final payload exit code
            if task.status in ["completed", "failed"]:
                final_payload = {
                    "status": task.status,
                    "report": task.report,
                    "plan": task.plan,
                    "findings": task.findings
                }
                yield f"data: {json.dumps({'agent': 'System', 'message': '__FINISHED__', 'payload': final_payload})}\n\n"
                break
                
            await asyncio.sleep(0.2)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
