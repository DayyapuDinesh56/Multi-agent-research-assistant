import re
from datetime import datetime
from typing import TypedDict, List, Dict, Any
from langchain_core.runnables import RunnableConfig
import google.generativeai as genai

# Define the shared agent state schema
class AgentState(TypedDict):
    topic: str
    api_key: str
    plan: List[str]
    findings: Dict[str, Any]
    report: str
    logs: List[Dict[str, Any]]
    status: str

# Helper to append structured log entries to the state and invoke log callbacks
def add_log(state: AgentState, config: RunnableConfig, agent: str, message: str):
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "agent": agent,
        "message": message
    }
    state["logs"].append(log_entry)
    
    # Trigger callback if available in LangGraph runtime config
    if config:
        cb = config.get("configurable", {}).get("log_callback")
        if cb:
            try:
                cb(log_entry)
            except Exception as e:
                print(f"RAG Log Callback Error: {e}")
                
    print(f"[{agent}] {message}")

def query_gemini(api_key: str, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """Queries Gemini 1.5 Flash using system instruction prompts."""
    genai.configure(api_key=api_key)
    
    generation_config = {}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
        
    model = genai.GenerativeModel(
        model_name='gemini-3.1-flash-lite',
        system_instruction=system_prompt,
        generation_config=generation_config
    )
    
    response = model.generate_content(user_prompt)
    return response.text.strip()
