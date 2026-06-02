import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import httpx
from app.main import app
from app.db import init_db

async def test_rest_endpoints():
    print("=== Running FastAPI Endpoints Unit Tests ===")
    
    # 1. Initialize DB first
    print("Test 1: Initializing DB structures...")
    try:
        await init_db()
        print("✓ DB initialized successfully!")
    except Exception as e:
        print(f"✗ DB initialization failed: {e}")
        return False
        
    # 2. Test API Endpoints using httpx AsyncClient pointing to app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # A. Test Create Job
        payload = {
            "prompt": "Evaluate the visual aesthetics of glassmorphism in modern dark-mode web designs",
            "depth": "basic"
        }
        print(f"\nTest 2: Creating research job via POST /api/research")
        response = await client.post("/api/research", json=payload)
        
        assert response.status_code == 200, f"Failed creation: {response.text}"
        data = response.json()
        assert "job_id" in data, "No job_id returned"
        job_id = data["job_id"]
        print(f"✓ Job created successfully! ID: {job_id} | Status: {data['status']}")
        
        # B. Test Get Job List
        print(f"\nTest 3: Retrieving job list via GET /api/research")
        list_response = await client.get("/api/research")
        assert list_response.status_code == 200
        jobs_list = list_response.json()
        assert len(jobs_list) > 0, "Job list empty"
        assert any(j["id"] == job_id for j in jobs_list), "Created job not found in list"
        print(f"✓ Job list retrieved. Found {len(jobs_list)} items. Verified created job is present.")
        
        # C. Test Get Job Details
        print(f"\nTest 4: Retrieving job details via GET /api/research/{job_id}")
        # Wait a small moment to let the initial planning step execute in background
        await asyncio.sleep(2)
        
        details_response = await client.get(f"/api/research/{job_id}")
        assert details_response.status_code == 200
        details = details_response.json()
        assert details["job_id"] == job_id
        print(f"✓ Job details retrieved.")
        print(f"  Title: {details['title']}")
        print(f"  Status in DB: {details['status']}")
        print(f"  Logs generated: {len(details['logs'])}")
        
        if details["logs"]:
            print(f"  Latest Log: {details['logs'][-1]}")
            
    print("\n✓ ALL REST API TESTS PASSED SUCCESSFULLY!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_rest_endpoints())
    sys.exit(0 if success else 1)
