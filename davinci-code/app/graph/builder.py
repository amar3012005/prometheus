"""LangGraph State Machine Builder"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.state import AgentState
from app.graph.nodes import (
    entry_node,
    extraction_node,
    validator_node,
    generation_node,
    finalize_node,
    build_node,
    should_validate,
    check_voice_selection
)

def create_agent_graph():
    """
    Build the LangGraph state machine for agent creation.
    
    Flow:
        entry -> extraction -> validator -> [interrupt] OR [generation -> [interrupt-for-voice] -> finalize -> build -> END]
    """
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("entry", entry_node)
    workflow.add_node("extraction", extraction_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("build", build_node)
    
    # Define edges
    workflow.set_entry_point("entry")
    workflow.add_edge("entry", "extraction")
    workflow.add_edge("extraction", "validator")
    
    # Conditional edge from validator
    workflow.add_conditional_edges(
        "validator",
        should_validate,
        {
            "generation": "generation",
            "interrupt": END  # Will be handled by checkpointer for human-in-the-loop
        }
    )
    
    # Conditional edge for voice selection
    workflow.add_conditional_edges(
        "generation",
        check_voice_selection,
        {
            "finalize": "finalize",
            "interrupt": "finalize" # This won't be reached if we handle interrupts correctly
        }
    )
    
    workflow.add_edge("finalize", "build")
    workflow.add_edge("build", END)
    
    # Compile with memory for human-in-the-loop
    checkpointer = MemorySaver()
    
    graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["generation"], # Pause for voice selection
        interrupt_before=["build"]     # Pause for "Let's Build" click
    )
    
    return graph

# Singleton graph instance
agent_graph = create_agent_graph()
