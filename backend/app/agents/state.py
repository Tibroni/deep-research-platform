from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages

def append_logs(left: List[str], right: List[str]) -> List[str]:
    """Helper to accumulate terminal-style execution logs."""
    return left + right

class ResearchState(TypedDict):
    # User's initial prompt and instructions
    prompt: str
    
    # Selected depth ('basic' or 'deep')
    depth: str
    
    # Structured plan outline: list of research tracks/topics
    # Example: [{"id": 1, "topic": "Evolution of Agent SDKs", "queries": ["LangGraph 2025 updates", "crewai vs langgraph"], "completed": False}]
    plan: List[Dict[str, Any]]
    
    # Scraped contents of pages
    # Example: [{"source_id": "S1", "url": "url", "text": "full text..."}]
    findings: List[Dict[str, Any]]
    
    # Claims extracted for verification
    # Example: [{"claim": "LangGraph added native Postgres Checkpointer in late 2024", "source_id": "S1"}]
    claims: List[Dict[str, Any]]
    
    # Fact Checking evaluations and flags
    # Example: [{"claim": "...", "status": "verified|contradicted|hallucination", "notes": "..."}]
    fact_checking_report: List[Dict[str, Any]]
    
    # Current draft report in Markdown
    draft_report: str
    
    # Human or Reviewer revision feedback
    revision_feedback: str
    
    # Citations dictionary mapping Source ID to title and URL
    # Example: [{"id": "S1", "title": "LangGraph Doc", "url": "https://...", "snippet": "..."}]
    sources: List[Dict[str, Any]]
    
    # System logs representing the current node thoughts & actions
    node_logs: Annotated[List[str], append_logs]
    
    # Chat message log (allows conversational multi-agent structure)
    messages: Annotated[List[Any], add_messages]
