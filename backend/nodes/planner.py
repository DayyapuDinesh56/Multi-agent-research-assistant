import json
import re
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from backend.nodes.state import AgentState, add_log, query_gemini

def planner_node(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Planner Agent: Analyzes the topic and generates 3-5 research questions."""
    add_log(state, config, "Planner", "Analyzing topic and breaking it down into sub-questions...")
    
    system_prompt = (
        "You are a Senior Research Planner. Your task is to analyze a complex research topic/question "
        "and break it down into 3 to 5 distinct, highly focused sub-questions or research areas.\n"
        "These sub-questions will be used by a Researcher agent to retrieve information from a document library.\n"
        "Each sub-question must be concise, specific, and designed to gather facts from documents.\n"
        "You must return your response as a JSON object matching this schema:\n"
        '{\n  "sub_questions": ["sub-question 1", "sub-question 2", ...]\n}'
    )
    
    user_prompt = f"Research Topic: {state['topic']}"
    
    sub_questions = []
    try:
        response_text = query_gemini(state["api_key"], system_prompt, user_prompt, json_mode=True)
        
        try:
            data = json.loads(response_text)
            if isinstance(data, dict) and "sub_questions" in data:
                sub_questions = [q.strip() for q in data["sub_questions"] if q.strip()]
        except Exception:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                sub_questions = data.get("sub_questions", [])
                
        if not sub_questions:
            raise ValueError("No sub-questions parsed from LLM output")
            
        add_log(state, config, "Planner", f"Successfully generated {len(sub_questions)} research sub-questions:")
        for idx, sq in enumerate(sub_questions):
            add_log(state, config, "Planner", f"  {idx+1}. {sq}")
            
    except Exception as e:
        add_log(state, config, "Planner", f"Warning: Planner failed to generate JSON ({e}). Utilizing fallback plan.")
        sub_questions = [
            f"Overview and definitions regarding {state['topic']}",
            f"Key findings and developments about {state['topic']}",
            f"Applications, challenges, and references for {state['topic']}"
        ]
        
    return {
        "plan": sub_questions,
        "logs": state["logs"],
        "status": "researching"
    }
