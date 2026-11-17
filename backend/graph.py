from langgraph.graph import StateGraph, END
from backend.nodes.state import AgentState
from backend.nodes.planner import planner_node
from backend.nodes.researcher import researcher_node
from backend.nodes.writer import writer_node

def create_research_graph():
    """Builds and compiles the sequential state graph."""
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    
    # Set Entry Point
    workflow.set_entry_point("planner")
    
    # Set Transitions
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END)
    
    return workflow.compile()
