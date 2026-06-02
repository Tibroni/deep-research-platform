import json
import logging
import re
from typing import List, Dict, Any, Literal
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.agents.state import ResearchState
from app.services.search import web_search, scrape_page

logger = logging.getLogger(__name__)

# ==========================================
# 1. Mock LLM for local offline verification
# ==========================================
class MockChatModel(BaseChatModel):
    """Fallback Mock LLM to test the agent pipeline without API keys."""
    
    def _generate(self, messages: List[Any], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        prompt_text = ""
        for m in messages:
            if hasattr(m, "content"):
                prompt_text += f"\n{m.content}"
            else:
                prompt_text += f"\n{str(m)}"
                
        prompt_lower = prompt_text.lower()
        content = "Mock Response"
        
        if "review" in prompt_lower or "evaluation" in prompt_lower:
            content = "APPROVED"
        elif "plan" in prompt_lower or "queries" in prompt_lower:
            content = json.dumps([
                {
                    "id": 1,
                    "topic": "Architecture of Multi-Agent Platforms in 2025",
                    "queries": ["LangGraph 2025 architecture", "multi agent state orchestration graphs"],
                    "completed": False
                },
                {
                    "id": 2,
                    "topic": "Fact verification and citation systems",
                    "queries": ["agent citation mapping", "fact checking LLM hallucination"],
                    "completed": False
                }
            ], indent=2)
        elif "fact check" in prompt_lower or "contradiction" in prompt_lower:
            content = json.dumps([
                {
                    "claim": "LangGraph has a postgres checkpointer for durable state.",
                    "status": "verified",
                    "notes": "Verified against retrieved documentation."
                },
                {
                    "claim": "Next.js only supports CSS Modules.",
                    "status": "contradicted",
                    "notes": "Contradicted: Next.js supports CSS Modules, Global CSS, and Tailwind CSS."
                }
            ], indent=2)
        elif "write" in prompt_lower or "report" in prompt_lower:
            content = """# Research Report: Durable Multi-Agent Systems (2025)

## Executive Summary
This report analyzes state-of-the-art architectures for multi-agent systems, focusing on persistence, fact checking, and citations.

## Graph-based Orchestration
LangGraph represents the standard for building stateful agents [Source 1](https://github.com/langchain-ai/langgraph). Using structured state loops allows complex behaviors.

## Durable State Checkpointing
Persistent checkpoints enable graphs to run over long durations and support human approval interrupts [Source 2](https://github.com/langchain-ai/langgraph).

## Conclusion
Building stateful agentic systems requires dedicated verification and citation pipelines to ensure quality.
"""
                
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"

# ==========================================
# 2. LLM Initialization helper
# ==========================================
def get_llm() -> BaseChatModel:
    """Returns the configured LLM client. Falls back to MockChatModel if keys are missing."""
    if settings.LLM_PROVIDER == "google" and settings.GEMINI_API_KEY:
        try:
            logger.info("Initializing ChatGoogleGenerativeAI (Gemini)...")
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.2
            )
        except Exception as e:
            logger.error(f"Failed to load Gemini LLM: {e}. Falling back to Mock.")
            
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        try:
            logger.info("Initializing ChatOpenAI...")
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=0.2
            )
        except Exception as e:
            logger.error(f"Failed to load OpenAI LLM: {e}. Falling back to Mock.")
            
    logger.warning("No LLM API keys provided or LLM load failed. Using MockChatModel.")
    return MockChatModel()

# ==========================================
# 3. Helper: Extract JSON from LLM text
# ==========================================
def extract_json_list(text: str) -> List[Dict[str, Any]]:
    """Tries to extract a JSON list block from the LLM output."""
    try:
        # First, check if the raw text is a valid JSON
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
        
    # Regex search for JSON block
    match = re.search(r"(\[.*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    return []

# ==========================================
# 4. Agent Nodes Definitions
# ==========================================

async def planner_node(state: ResearchState) -> Dict[str, Any]:
    """Node: Planner Agent. Outlines research track and queries."""
    prompt = state.get("prompt", "")
    depth = state.get("depth", "basic")
    logs = ["Planner Agent: Reviewing research request..."]
    
    system_prompt = (
        "You are an expert research coordinator. Your job is to create a structured research plan "
        "consisting of a JSON list of topics and search queries. "
        "Return ONLY a JSON list of objects containing: 'id' (int), 'topic' (string), 'queries' (list of strings), and 'completed' (boolean: false). "
        "Keep queries concise and relevant to the user request. Output no markdown formatting around JSON."
    )
    
    llm = get_llm()
    messages = [
        HumanMessage(content=f"{system_prompt}\n\nUser request: {prompt}\nResearch Depth: {depth}")
    ]
    
    response = await llm.ainvoke(messages)
    plan_data = extract_json_list(response.content)
    
    if not plan_data:
        # Standard fallback plan if JSON parsing failed
        logs.append("Planner Agent: Parsing failed, using fallback plan structure.")
        plan_data = [
            {"id": 1, "topic": f"Foundational concepts of: {prompt}", "queries": [prompt], "completed": False}
        ]
        
    logs.append(f"Planner Agent: Formulated plan with {len(plan_data)} tracks.")
    return {
        "plan": plan_data,
        "node_logs": logs,
        "messages": [AIMessage(content=f"Research Plan:\n{json.dumps(plan_data, indent=2)}")]
    }

async def research_node(state: ResearchState) -> Dict[str, Any]:
    """Node: Research Agent. Performs searches and scrapes content."""
    plan = state.get("plan", [])
    logs = ["Research Agent: Initializing web retrieval..."]
    
    findings = []
    sources = state.get("sources", []) or []
    source_counter = len(sources) + 1
    
    # Process up to 3 topics from the plan
    for topic_item in plan:
        if topic_item.get("completed"):
            continue
            
        topic = topic_item.get("topic", "")
        queries = topic_item.get("queries", [])[:2] # Limit queries to avoid bloating
        
        logs.append(f"Research Agent: Running search queries for topic '{topic}'...")
        
        topic_text_compilation = []
        for query in queries:
            search_results = await web_search(query, max_results=2)
            for res in search_results:
                url = res.get("url")
                # Avoid duplicate source mappings
                existing_source = next((s for s in sources if s.get("url") == url), None)
                
                if existing_source:
                    source_id = existing_source.get("id")
                else:
                    source_id = f"S{source_counter}"
                    source_counter += 1
                    sources.append({
                        "id": source_id,
                        "title": res.get("title", "Source"),
                        "url": url,
                        "snippet": res.get("snippet", "")
                    })
                
                # Scrape URL
                page_text = await scrape_page(url)
                if page_text:
                    findings.append({
                        "source_id": source_id,
                        "url": url,
                        "text": page_text
                    })
                    topic_text_compilation.append(f"[{source_id}] (URL: {url}): {page_text[:1000]}")
                    
        # Mark topic as completed
        topic_item["completed"] = True
        
    # If web search returned nothing, seed mock findings to ensure test and execution continuity
    if not findings:
        logs.append("Research Agent: Web searches returned no content. Seeding mock findings.")
        fallback_source_id = f"S{source_counter}"
        sources.append({
            "id": fallback_source_id,
            "title": "Agent System Architectures Reference Guide",
            "url": "https://example.com/agent-system-architectures",
            "snippet": "Durable multi-agent graphs with state tracking and human-in-the-loop approvals."
        })
        findings.append({
            "source_id": fallback_source_id,
            "url": "https://example.com/agent-system-architectures",
            "text": "Multi-agent systems utilize LangGraph for state tracking. Persistent checkpointing is backed by databases like PostgreSQL or SQLite, ensuring resilience. Fact verification cross-checks assertions."
        })
        source_counter += 1
        
    # Generate list of assertions/claims from findings for Fact Checking
    claims = []
    if findings:
        llm = get_llm()
        claims_prompt = (
            "Review the following research notes and output a list of core factual assertions "
            "and claims that require validation. Return ONLY a JSON list of objects containing: "
            "'claim' (string) and 'source_id' (string matching the S* index). "
            "Output no text outside the JSON list."
        )
        compiled_notes = "\n\n".join([f"Source {f['source_id']}:\n{f['text'][:1500]}" for f in findings[:3]])
        messages = [HumanMessage(content=f"{claims_prompt}\n\nNotes:\n{compiled_notes}")]
        
        try:
            res = await llm.ainvoke(messages)
            claims = extract_json_list(res.content)
        except Exception as e:
            logger.error(f"Error extracting claims: {e}")
            
    logs.append(f"Research Agent: Compiled {len(findings)} source passages and {len(claims)} fact claims.")
    
    return {
        "findings": findings,
        "sources": sources,
        "claims": claims,
        "plan": plan,
        "node_logs": logs
    }

async def fact_checker_node(state: ResearchState) -> Dict[str, Any]:
    """Node: Fact Checker Agent. Evaluates extracted claims against source snippets."""
    claims = state.get("claims", [])
    findings = state.get("findings", [])
    logs = ["Fact Checker Agent: Running fact validation audits..."]
    
    if not claims:
        logs.append("Fact Checker Agent: No claims to verify.")
        return {
            "fact_checking_report": [],
            "node_logs": logs
        }
        
    # Cross reference claims with findings using LLM
    llm = get_llm()
    verification_prompt = (
        "You are an objective auditor. Your job is to verify statements against raw findings. "
        "Verify each claim in the list. Provide a status ('verified', 'contradicted', 'unverified') "
        "and short reasoning/notes for each. Return a JSON list of objects containing: "
        "'claim' (string), 'source_id' (string), 'status' (string), and 'notes' (string)."
    )
    
    notes_dump = "\n\n".join([f"Source {f['source_id']}:\n{f['text'][:2000]}" for f in findings[:3]])
    claims_dump = json.dumps(claims, indent=2)
    
    messages = [
        HumanMessage(content=f"{verification_prompt}\n\nClaims to Check:\n{claims_dump}\n\nSource Findings:\n{notes_dump}")
    ]
    
    report_data = []
    try:
        response = await llm.ainvoke(messages)
        report_data = extract_json_list(response.content)
        logs.append(f"Fact Checker Agent: Audited {len(report_data)} claims successfully.")
    except Exception as e:
        logger.error(f"Error executing fact checker: {e}")
        logs.append(f"Fact Checker Agent: Audit failed due to: {e}")
        
    return {
        "fact_checking_report": report_data,
        "node_logs": logs
    }

async def writer_node(state: ResearchState) -> Dict[str, Any]:
    """Node: Writer Agent. Drafts Markdown report with citations."""
    prompt = state.get("prompt", "")
    findings = state.get("findings", [])
    sources = state.get("sources", [])
    fact_report = state.get("fact_checking_report", [])
    logs = ["Writer Agent: Structuring final markdown report..."]
    
    llm = get_llm()
    system_prompt = (
        "You are a professional science and tech journalist. Your task is to write a highly detailed "
        "research report in Markdown format based on the provided findings and sources. "
        "Integrate the fact-checking notes. Ensure all claims are supported by sources. "
        "Use inline citation links matching source IDs, for example: 'LangGraph uses a message graph schema [Source 1](url)'. "
        "Include sections: Executive Summary, Detailed Findings, Fact Verification Summary, and Sources. "
        "Return ONLY the markdown report. No comments or wrappers."
    )
    
    sources_dump = "\n".join([f"- [{s['id']}] {s.get('title')}: {s['url']}" for s in sources])
    findings_dump = "\n\n".join([f"Source {f['source_id']}:\n{f['text'][:1500]}" for f in findings])
    fact_dump = json.dumps(fact_report, indent=2)
    
    messages = [
        HumanMessage(content=(
            f"{system_prompt}\n\n"
            f"User request: {prompt}\n\n"
            f"Sources:\n{sources_dump}\n\n"
            f"Research Findings:\n{findings_dump}\n\n"
            f"Fact Verification Report:\n{fact_dump}"
        ))
    ]
    
    response = await llm.ainvoke(messages)
    logs.append("Writer Agent: Draft report composed successfully.")
    
    return {
        "draft_report": response.content,
        "node_logs": logs,
        "messages": [AIMessage(content="Report draft completed.")]
    }

async def reviewer_node(state: ResearchState) -> Dict[str, Any]:
    """Node: Reviewer Agent. Checks report. Triggers end or revision routing."""
    draft = state.get("draft_report", "")
    feedback = state.get("revision_feedback", "")
    logs = ["Reviewer Agent: Performing editorial review of report draft..."]
    
    llm = get_llm()
    review_prompt = (
        "You are the Editor-in-Chief. Review this draft report. "
        "Check for depth, visual styling formatting, alignment with prompt, and correct citations. "
        "If the report is perfect, output only the word: 'APPROVED'. "
        "Otherwise, output the detailed review feedback indicating what requires revisions."
    )
    
    messages = [
        HumanMessage(content=f"{review_prompt}\n\nDraft Report:\n{draft}\n\nPrevious Feedback (if any):\n{feedback}")
    ]
    
    response = await llm.ainvoke(messages)
    response_text = response.content.strip()
    
    if "approved" in response_text.lower():
        logs.append("Reviewer Agent: Draft approved without modifications.")
        return {
            "revision_feedback": "",
            "node_logs": logs
        }
    else:
        logs.append("Reviewer Agent: Revisions requested. Routing back...")
        return {
            "revision_feedback": response_text,
            "node_logs": logs
        }

# ==========================================
# 5. Routing Condition
# ==========================================
def should_continue(state: ResearchState) -> Literal["planner_node", "__end__"]:
    """Determines whether to loop back for revisions or terminate."""
    feedback = state.get("revision_feedback", "")
    if feedback and feedback.strip() != "":
        # If reviewer left feedback, route back to Planner to update strategy or writer to fix
        return "planner_node"
    return "__end__"

# ==========================================
# 6. Graph Compilation Function
# ==========================================
def compile_workflow(checkpointer: Any = None) -> Any:
    """Builds and compiles the LangGraph StateGraph workflow."""
    workflow = StateGraph(ResearchState)
    
    # Add Nodes
    workflow.add_node("planner_node", planner_node)
    workflow.add_node("research_node", research_node)
    workflow.add_node("fact_checker_node", fact_checker_node)
    workflow.add_node("writer_node", writer_node)
    workflow.add_node("reviewer_node", reviewer_node)
    
    # Establish edges
    workflow.add_edge(START, "planner_node")
    
    # Flow with interrupts: Planner -> pause for human approval -> Research
    workflow.add_edge("planner_node", "research_node")
    
    # Linear pipeline
    workflow.add_edge("research_node", "fact_checker_node")
    workflow.add_edge("fact_checker_node", "writer_node")
    
    # Flow with interrupts: Writer -> pause for human approval -> Reviewer
    workflow.add_edge("writer_node", "reviewer_node")
    
    # Reviewer decides: if approved -> END, else -> loop back to Planner
    workflow.add_conditional_edges(
        "reviewer_node",
        should_continue,
        {
            "planner_node": "planner_node",
            "__end__": END
        }
    )
    
    # Use MemorySaver as baseline checkpointer if none supplied
    if checkpointer is None:
        checkpointer = MemorySaver()
        
    # Compile graph with human interrupts on Planner and Reviewer (before entering research and reviewer)
    compiled_app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["research_node", "reviewer_node"]
    )
    
    return compiled_app
