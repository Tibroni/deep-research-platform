import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings, BASE_DIR
from app.db import (
    init_db, get_db, ResearchJob, Report, Source, HumanFeedback
)
from app.agents.graph import compile_workflow

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("deep-research-backend")

app = FastAPI(title="Deep Research Agent API", version="1.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS allow_origins: %s", settings.cors_origins)
if settings.cors_origin_regex:
    logger.info("CORS allow_origin_regex: %s", settings.cors_origin_regex)

# ==========================================
# 1. WebSocket Broadcast Manager
# ==========================================
class ConnectionManager:
    def __init__(self):
        # Maps job_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info(f"WebSocket connected for job: {job_id}. Active: {len(self.active_connections[job_id])}")

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"WebSocket disconnected for job: {job_id}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_job(self, job_id: str, message: dict):
        if job_id in self.active_connections:
            logger.info(f"Broadcasting websocket update to {len(self.active_connections[job_id])} clients for job {job_id}")
            # Gather broadcasts
            await asyncio.gather(
                *[conn.send_json(message) for conn in self.active_connections[job_id]],
                return_exceptions=True
            )

ws_manager = ConnectionManager()

# ==========================================
# ==========================================
# 2. Checkpointer Initialization
# ==========================================
_global_checkpointer = None
_sqlite_conn = None
_postgres_pool = None

def get_checkpointer():
    """Gets the persistent checkpointer. Falls back to MemorySaver if not initialized yet."""
    global _global_checkpointer
    if _global_checkpointer is not None:
        return _global_checkpointer
    from langgraph.checkpoint.memory import MemorySaver
    _global_checkpointer = MemorySaver()
    return _global_checkpointer

# Initialize compiled graph with persistent checkpointer
def get_graph():
    checkpointer = get_checkpointer()
    return compile_workflow(checkpointer)

# ==========================================
# 3. Startup & Database Hook
# ==========================================
@app.on_event("startup")
async def startup_event():
    global _global_checkpointer, _sqlite_conn, _postgres_pool
    logger.info("Initializing Postgres/SQLite database schemas...")
    await init_db()
    logger.info("✓ Business database schemas initialized.")
    
    # Initialize checkpointer
    if settings.DATABASE_URL:
        try:
            logger.info("Setting up PostgreSQL Saver...")
            from psycopg_pool import ConnectionPool
            from langgraph.checkpoint.postgres import PostgresSaver
            
            conn_info = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            _postgres_pool = ConnectionPool(conninfo=conn_info, max_size=10, open=True)
            checkpointer = PostgresSaver(_postgres_pool)
            checkpointer.setup()
            _global_checkpointer = checkpointer
            logger.info("✓ PostgreSQL Checkpointer running.")
            return
        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL Saver: {e}. Falling back to SQLite.")

    # Option 2: SQLite Async Checkpointer
    try:
        logger.info("Setting up Async SQLite Saver...")
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        
        db_path = BASE_DIR / "deep_research_checkpoints.db"
        _sqlite_conn = await aiosqlite.connect(str(db_path))
        checkpointer = AsyncSqliteSaver(_sqlite_conn)
        await checkpointer.setup()
        
        _global_checkpointer = checkpointer
        logger.info("✓ Async SQLite Checkpointer running.")
    except Exception as e:
        logger.error(f"Failed to setup Async SQLite Saver: {e}. Falling back to Memory Saver.")
        from langgraph.checkpoint.memory import MemorySaver
        _global_checkpointer = MemorySaver()

@app.on_event("shutdown")
async def shutdown_event():
    global _sqlite_conn, _postgres_pool
    logger.info("Shutting down databases...")
    if _sqlite_conn:
        await _sqlite_conn.close()
        logger.info("✓ SQLite checkpointer connection closed.")
    if _postgres_pool:
        _postgres_pool.close()
        logger.info("✓ PostgreSQL connection pool closed.")

# ==========================================
# 4. Background Graph Runner
# ==========================================
async def execute_graph_background(job_id: str, inputs: Optional[dict] = None):
    """
    Executes or resumes a LangGraph thread in the background, streams events to WebSockets,
    and updates the job status database tables.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": job_id}}
    
    # Broadcast start of execution
    await ws_manager.broadcast_to_job(job_id, {"type": "status_update", "status": "executing", "message": "Graph started..."})
    
    # Setup database write connection
    from app.db import async_session
    
    try:
        # Run graph execution stream
        async for event in graph.astream(inputs, config, stream_mode="values"):
            # Whenever the state updates, get the latest node logs and draft reports to broadcast
            node_logs = event.get("node_logs", [])
            latest_log = node_logs[-1] if node_logs else "Running node..."
            
            # Broadcast state packet to the client
            await ws_manager.broadcast_to_job(job_id, {
                "type": "state_update",
                "logs": node_logs,
                "latest_log": latest_log,
                "plan": event.get("plan", []),
                "draft_report": event.get("draft_report", ""),
                "sources": event.get("sources", []),
                "fact_checking_report": event.get("fact_checking_report", [])
            })
            
        # Post-execution status auditing
        state = await graph.aget_state(config)
        next_nodes = state.next
        
        # Default job status
        db_status = "completed"
        
        if next_nodes:
            next_node = next_nodes[0]
            if next_node == "research_node":
                db_status = "awaiting_plan_approval"
            elif next_node == "reviewer_node":
                db_status = "awaiting_final_approval"
            else:
                db_status = "pending"
                
        # Update Database Job Status
        async with async_session() as session:
            async with session.begin():
                # Fetch job and update
                stmt = (
                    update(ResearchJob)
                    .where(ResearchJob.id == job_id)
                    .values(status=db_status)
                )
                await session.execute(stmt)
                
                # If completed, persist report and sources mapping
                if db_status == "completed":
                    values = state.values
                    # 1. Insert Report
                    report_content = values.get("draft_report", "")
                    db_report = Report(job_id=job_id, content=report_content)
                    session.add(db_report)
                    
                    # 2. Insert Sources
                    for source_item in values.get("sources", []):
                        db_source = Source(
                            job_id=job_id,
                            title=source_item.get("title", "Source"),
                            url=source_item.get("url"),
                            snippet=source_item.get("snippet", "")
                        )
                        session.add(db_source)
                        
            logger.info(f"Background execution paused/completed for job {job_id}. Status: {db_status}")
            
        # Broadcast final status
        await ws_manager.broadcast_to_job(job_id, {
            "type": "status_update",
            "status": db_status,
            "message": f"Execution reached state: {db_status}"
        })
        
    except Exception as e:
        logger.error(f"Error in background execution for job {job_id}: {e}", exc_info=True)
        # Update database status to failed
        async with async_session() as session:
            async with session.begin():
                stmt = (
                    update(ResearchJob)
                    .where(ResearchJob.id == job_id)
                    .values(status="failed")
                )
                await session.execute(stmt)
        await ws_manager.broadcast_to_job(job_id, {
            "type": "status_update",
            "status": "failed",
            "message": f"Execution failed: {str(e)}"
        })

# ==========================================
# 5. Pydantic Models for REST Endpoints
# ==========================================
class CreateJobRequest(BaseModel):
    prompt: str
    depth: str = "basic"  # "basic" or "deep"

class ApprovePlanRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None

class ApproveReportRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None

# ==========================================
# 6. REST API Routes
# ==========================================

@app.post("/api/research")
async def create_research_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Creates a new research job, initializes state in DB, and triggers graph in background."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
    # 1. Create ResearchJob DB row
    import uuid
    job_id = str(uuid.uuid4())
    # Generate title from prompt (truncated)
    title = request.prompt[:50] + "..." if len(request.prompt) > 50 else request.prompt
    job = ResearchJob(
        id=job_id,
        title=title,
        prompt=request.prompt,
        status="planning",
        thread_id=job_id
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # 2. Trigger initial graph run
    initial_state = {
        "prompt": request.prompt,
        "depth": request.depth,
        "plan": [],
        "findings": [],
        "claims": [],
        "fact_checking_report": [],
        "draft_report": "",
        "revision_feedback": "",
        "sources": [],
        "node_logs": ["System: Starting research workflow orchestrator..."],
        "messages": []
    }
    
    background_tasks.add_task(execute_graph_background, str(job.id), initial_state)
    
    return {
        "job_id": str(job.id),
        "title": job.title,
        "status": job.status,
        "created_at": job.created_at
    }

@app.get("/api/research")
async def list_research_jobs(db: AsyncSession = Depends(get_db)):
    """Lists all research jobs in reverse chronological order."""
    result = await db.execute(select(ResearchJob).order_by(ResearchJob.created_at.desc()))
    jobs = result.scalars().all()
    return [
        {
            "id": job.id,
            "title": job.title,
            "prompt": job.prompt,
            "status": job.status,
            "created_at": job.created_at
        } for job in jobs
    ]

@app.get("/api/research/{job_id}")
async def get_research_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves full job status details from SQL and the active LangGraph thread state."""
    # 1. Fetch from DB
    result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
        
    # 2. Retrieve state from LangGraph
    graph = get_graph()
    config = {"configurable": {"thread_id": job_id}}
    state = await graph.aget_state(config)
    
    # Values represent the current agent state dictionary
    values = state.values if state.values else {}
    next_action = state.next if state.next else []
    
    return {
        "job_id": str(job.id),
        "title": job.title,
        "prompt": job.prompt,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "plan": values.get("plan", []),
        "draft_report": values.get("draft_report", ""),
        "sources": values.get("sources", []),
        "fact_checking_report": values.get("fact_checking_report", []),
        "logs": values.get("node_logs", []),
        "next_step": next_action
    }

@app.post("/api/research/{job_id}/approve-plan")
async def approve_research_plan(
    job_id: str,
    request: ApprovePlanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handles Human-in-the-Loop decision on the research plan."""
    # 1. Fetch job from DB
    result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "awaiting_plan_approval":
        raise HTTPException(status_code=400, detail="Job is not awaiting plan approval")
        
    # Save feedback record in DB
    feedback = HumanFeedback(
        job_id=job_id,
        step_name="plan_approval",
        approved=request.approved,
        feedback_text=request.feedback
    )
    db.add(feedback)
    
    # 2. Modify State and Resume
    graph = get_graph()
    config = {"configurable": {"thread_id": job_id}}
    
    if request.approved:
        # If human edited the plan topics on the UI, update the state values
        state_updates = {}
        if request.plan:
            state_updates["plan"] = request.plan
            
        # We tell LangGraph that the plan was approved (clear feedback)
        state_updates["revision_feedback"] = ""
        state_updates["node_logs"] = ["User: Approved research plan. Commencing deep retrieval..."]
        
        await graph.aupdate_state(config, state_updates, as_node="planner_node")
        
        # Resume the graph background process (inputs=None resumes from pause)
        background_tasks.add_task(execute_graph_background, job_id, None)
        
    else:
        # Rejected plan
        feedback_msg = request.feedback or "Plan rejected by user without specific comments."
        state_updates = {
            "revision_feedback": feedback_msg,
            "node_logs": [f"User: Rejected plan. Feedback: {feedback_msg}"]
        }
        # Update state and resume. It will loop back to planner_node
        await graph.aupdate_state(config, state_updates, as_node="planner_node")
        background_tasks.add_task(execute_graph_background, job_id, None)
        
    # Set status back to executing in database
    job.status = "executing"
    await db.commit()
    
    return {"status": "resumed"}

@app.post("/api/research/{job_id}/approve-report")
async def approve_research_report(
    job_id: str,
    request: ApproveReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handles Human-in-the-Loop decision on the final drafted report."""
    result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "awaiting_final_approval":
        raise HTTPException(status_code=400, detail="Job is not awaiting report approval")
        
    # Save feedback record in DB
    feedback = HumanFeedback(
        job_id=job_id,
        step_name="final_approval",
        approved=request.approved,
        feedback_text=request.feedback
    )
    db.add(feedback)
    
    graph = get_graph()
    config = {"configurable": {"thread_id": job_id}}
    
    if request.approved:
        state_updates = {
            "revision_feedback": "",
            "node_logs": ["User: Final report approved. Document finalized."]
        }
        await graph.aupdate_state(config, state_updates, as_node="reviewer_node")
        background_tasks.add_task(execute_graph_background, job_id, None)
    else:
        feedback_msg = request.feedback or "Report rejected without specific comments."
        state_updates = {
            "revision_feedback": feedback_msg,
            "node_logs": [f"User: Requested report revisions. Feedback: {feedback_msg}"]
        }
        # Routes back to writer or planner
        await graph.aupdate_state(config, state_updates, as_node="reviewer_node")
        background_tasks.add_task(execute_graph_background, job_id, None)
        
    job.status = "executing"
    await db.commit()
    
    return {"status": "resumed"}

@app.get("/api/research/{job_id}/report")
async def get_completed_report(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves finalized report output."""
    result = await db.execute(select(Report).where(Report.job_id == job_id).order_by(Report.created_at.desc()))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this job")
        
    # Fetch sources
    src_result = await db.execute(select(Source).where(Source.job_id == job_id))
    sources = src_result.scalars().all()
    
    return {
        "job_id": job_id,
        "content": report.content,
        "created_at": report.created_at,
        "sources": [
            {
                "title": s.title,
                "url": s.url,
                "snippet": s.snippet
            } for s in sources
        ]
    }

# ==========================================
# 7. WebSockets Real-Time Stream Endpoint
# ==========================================
@app.websocket("/ws/research/{job_id}")
async def research_websocket_endpoint(websocket: WebSocket, job_id: str):
    """Establishes real-time push streams of agent logs and workflow states."""
    await ws_manager.connect(websocket, job_id)
    
    # Immediately push current status
    graph = get_graph()
    config = {"configurable": {"thread_id": job_id}}
    try:
        state = await graph.aget_state(config)
        if state.values:
            await ws_manager.send_personal_message({
                "type": "state_update",
                "logs": state.values.get("node_logs", []),
                "latest_log": state.values.get("node_logs", [])[-1] if state.values.get("node_logs") else "Connection established.",
                "plan": state.values.get("plan", []),
                "draft_report": state.values.get("draft_report", ""),
                "sources": state.values.get("sources", []),
                "fact_checking_report": state.values.get("fact_checking_report", [])
            }, websocket)
    except Exception as e:
        logger.error(f"Error fetching state on websocket init: {e}")
        
    try:
        while True:
            # We don't expect client messages (read-only stream), but we must listen to keep connection alive
            # and detect client disconnects
            data = await websocket.receive_text()
            logger.info(f"Received client socket data: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)
    except Exception as e:
        logger.error(f"Error in websocket loop: {e}")
        ws_manager.disconnect(websocket, job_id)

# Helper to run the server directly if invoked
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
