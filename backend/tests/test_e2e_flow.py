import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import httpx
from app.main import app
from app.db import init_db

async def run_e2e_flow_validation():
    print("=== Running End-to-End Workflow Validation ===")
    
    # 1. Initialize SQLite database schemas
    print("Step 1: Setting up database structures...")
    await init_db()
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        
        # 2. Create Job
        prompt = "Benchmarking Edge AI acceleration in 2026"
        print(f"\nStep 2: Triggering new research job for prompt: '{prompt}'")
        res = await client.post("/api/research", json={"prompt": prompt, "depth": "basic"})
        assert res.status_code == 200, f"Creation failed: {res.text}"
        job_data = res.json()
        job_id = job_data["job_id"]
        print(f"✓ Job created! ID: {job_id} | Status: {job_data['status']}")
        
        # 3. Wait/Poll for Plan Approval Interrupt
        print("\nStep 3: Waiting for Planner Agent to draft outline...")
        max_attempts = 10
        plan = []
        for attempt in range(max_attempts):
            await asyncio.sleep(1)
            status_res = await client.get(f"/api/research/{job_id}")
            assert status_res.status_code == 200
            status_data = status_res.json()
            db_status = status_data["status"]
            print(f"  [Poll {attempt + 1}] DB Status: {db_status}")
            
            if db_status == "awaiting_plan_approval":
                plan = status_data["plan"]
                print(f"✓ Planner finished! Outlined {len(plan)} research tracks.")
                break
        else:
            print("✗ Timeout waiting for plan approval state")
            return False
            
        assert len(plan) > 0, "No research plan generated"
        
        # 4. Modify plan and Approve
        print("\nStep 4: Submitting plan approval...")
        # Simulate human editing a query
        plan[0]["queries"].append("Edge AI NPU benchmarks 2026")
        
        approval_res = await client.post(
            f"/api/research/{job_id}/approve-plan",
            json={"approved": True, "plan": plan}
        )
        assert approval_res.status_code == 200
        print("✓ Plan approved submitted. Resuming execution...")
        
        # 5. Wait/Poll for Report Draft Interrupt
        print("\nStep 5: Waiting for Research, Fact Check, and Writer Agents...")
        report_draft = ""
        for attempt in range(max_attempts):
            # Give it more time because it performs searches and scrapes page fallbacks
            await asyncio.sleep(2)
            status_res = await client.get(f"/api/research/{job_id}")
            assert status_res.status_code == 200
            status_data = status_res.json()
            db_status = status_data["status"]
            print(f"  [Poll {attempt + 1}] DB Status: {db_status}")
            
            if db_status == "awaiting_final_approval":
                report_draft = status_data["draft_report"]
                print(f"✓ Writer finished! Generated markdown report draft.")
                break
        else:
            print("✗ Timeout waiting for report approval state")
            return False
            
        assert len(report_draft) > 0, "No draft report generated"
        
        # 6. Approve Report
        print("\nStep 6: Submitting final report approval...")
        report_approval_res = await client.post(
            f"/api/research/{job_id}/approve-report",
            json={"approved": True}
        )
        assert report_approval_res.status_code == 200
        print("✓ Final approval submitted. Committing to DB...")
        
        # 7. Wait/Poll for Completion and Database Persistence Check
        print("\nStep 7: Verifying job completion and table storage...")
        for attempt in range(max_attempts):
            await asyncio.sleep(1)
            status_res = await client.get(f"/api/research/{job_id}")
            status_data = status_res.json()
            db_status = status_data["status"]
            print(f"  [Poll {attempt + 1}] DB Status: {db_status}")
            
            if db_status == "completed":
                print("✓ Job finished execution! Next step nodes are empty.")
                break
        else:
            print("✗ Timeout waiting for completed status")
            return False
            
        # 8. Check reports database table
        print("\nStep 8: Reading persisted document from database via endpoint...")
        doc_res = await client.get(f"/api/research/{job_id}/report")
        assert doc_res.status_code == 200, f"Report read failed: {doc_res.text}"
        doc_data = doc_res.json()
        assert len(doc_data["content"]) > 0, "Saved report content empty"
        assert len(doc_data["sources"]) > 0, "Saved citations empty"
        print(f"✓ Verified report stored in database: {len(doc_data['content'])} characters.")
        print(f"✓ Verified source references stored in database: {len(doc_data['sources'])} sources.")
        for idx, src in enumerate(doc_data["sources"]):
            print(f"  [{idx + 1}] Citation {idx + 1}: {src['title']} -> {src['url']}")
            
        print("\n✓ E2E WORKFLOW COMPLETED & FULLY VALIDATED WITH ZERO ERRORS!")
        return True

if __name__ == "__main__":
    success = asyncio.run(run_e2e_flow_validation())
    sys.exit(0 if success else 1)
