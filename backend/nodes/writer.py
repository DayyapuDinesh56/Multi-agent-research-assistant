from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from backend.nodes.state import AgentState, add_log, query_gemini

def writer_node(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
    """Writer Agent: Synthesizes all sub-question answers into a structured briefing report."""
    add_log(state, config, "Writer", "Compiling findings and writing final briefing report...")
    
    research_context_blocks = []
    all_sources = set()
    
    for sq, data in state["findings"].items():
        research_context_blocks.append(
            f"### Sub-Question Analysis: {sq}\n"
            f"Findings:\n{data['synthesis']}\n"
        )
        all_sources.update(data["sources"])
        
    research_context = "\n\n".join(research_context_blocks)
    sources_list_str = "\n".join([f"- {src}" for src in sorted(all_sources)]) if all_sources else "- No documents referenced."
    
    system_prompt = (
        "You are a Lead Research Director and Technical Writer. Your goal is to synthesize raw research "
        "findings into a professional, publication-ready research briefing.\n"
        "You must structure the report with the following markdown headers:\n"
        "# [Report Title]\n"
        "## Executive Summary\n"
        "Provide a high-level summary (1-2 paragraphs) synthesizing the overall findings, context, and significance.\n"
        "## Key Takeaways\n"
        "Provide 3 to 5 critical takeaways as a bulleted list.\n"
        "## Detailed Findings\n"
        "Provide sections for each sub-topic. Use markdown sub-headers (###) for each sub-question. "
        "Write a coherent, detailed analysis for each section. Incorporate facts, figures, and inline source "
        "citations (e.g., [security_policy.pdf, p. 2]) as provided in the research context.\n"
        "## Source References\n"
        "List the documents referenced in the research (provided in the prompt).\n\n"
        "Rules:\n"
        "- Ground everything in the provided research findings. Do not add outside assumptions.\n"
        "- Format all headers, lists, and citations beautifully in Markdown.\n"
        "- Do not write placeholders like '[Insert Date]' or '[Your Name]'."
    )
    
    user_prompt = (
        f"Original Topic: {state['topic']}\n\n"
        f"Compiled Research Findings:\n"
        f"{research_context}\n\n"
        f"All Referenced Documents:\n"
        f"{sources_list_str}"
    )
    
    try:
        report = query_gemini(state["api_key"], system_prompt, user_prompt)
        add_log(state, config, "Writer", "Report compilation complete.")
    except Exception as e:
        add_log(state, config, "Writer", f"Error compiling report: {e}")
        report = (
            f"# Research Briefing: {state['topic']}\n\n"
            f"## Executive Summary\n"
            f"Failed to generate synthesis report. Raw findings below.\n\n"
            f"## Detailed Findings\n"
            f"{research_context}\n\n"
            f"## Source References\n"
            f"{sources_list_str}"
        )
        
    return {
        "report": report,
        "logs": state["logs"],
        "status": "completed"
    }
