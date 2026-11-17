from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from backend.nodes.state import AgentState, add_log, query_gemini

def researcher_node(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Researcher Agent: Queries RAG vector index and summarizes matches per sub-question."""
    add_log(state, config, "Researcher", "Starting document retrieval and analysis...")
    
    rag_engine = config.get("configurable", {}).get("rag_engine") if config else None
    if not rag_engine:
        add_log(state, config, "Researcher", "Error: RAGEngine not found in node config. Skipping search.")
        return {"logs": state["logs"], "status": "writing"}
        
    findings = {}
    
    for idx, sq in enumerate(state["plan"]):
        add_log(state, config, "Researcher", f"Querying RAG index for sub-question {idx+1}/{len(state['plan'])}: '{sq}'")
        
        # Search the Gemini Embeddings index
        chunks = rag_engine.search(state["api_key"], sq, top_k=4)
        
        if not chunks:
            add_log(state, config, "Researcher", "  -> No matching passages found in document library.")
            findings[sq] = {
                "synthesis": "No information found in internal documents.",
                "sources": []
            }
            continue
            
        add_log(state, config, "Researcher", f"  -> Retrieved {len(chunks)} relevant chunks. Synthesizing answers...")
        
        # Format the context block
        context_blocks = []
        for c_idx, c in enumerate(chunks):
            page_info = f", Page {c['page']}" if c.get("page") else ""
            context_blocks.append(
                f"--- DOCUMENT REF {c_idx+1} ---\n"
                f"Source File: {c['source']}{page_info}\n"
                f"Content:\n{c['text']}"
            )
        context_str = "\n\n".join(context_blocks)
        
        # Summarize context using Gemini
        system_prompt = (
            "You are an expert Research Analyst. Your task is to analyze the provided DOCUMENT REFs "
            "to answer the research question. You must ground your answer strictly in the provided content.\n"
            "Do not assume or extrapolate. If the documents do not contain the answer, say 'The document library "
            "does not contain relevant facts for this sub-topic.'\n"
            "Format your response as: \n"
            "1. A concise synthesis summary (1-3 sentences).\n"
            "2. A bulleted list of key facts, ending each bullet with the source file name and page number (e.g., [doc.pdf, p. 3])."
        )
        
        user_prompt = (
            f"Research Question: {sq}\n\n"
            f"Retrieved Document Context:\n"
            f"{context_str}"
        )
        
        try:
            synthesis = query_gemini(state["api_key"], system_prompt, user_prompt)
            sources = list(set([c["source"] for c in chunks]))
            findings[sq] = {
                "synthesis": synthesis,
                "sources": sources
            }
            add_log(state, config, "Researcher", f"  -> Finished synthesis. Citations: {', '.join(sources)}")
        except Exception as e:
            add_log(state, config, "Researcher", f"  -> Synthesis failed: {e}")
            findings[sq] = {
                "synthesis": f"Error synthesizing research chunk: {e}",
                "sources": []
            }
            
    return {
        "findings": findings,
        "logs": state["logs"],
        "status": "writing"
    }
