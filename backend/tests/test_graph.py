import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.agents.graph import compile_workflow
from langgraph.checkpoint.memory import MemorySaver

async def run_graph_test():
    print("=== Testing LangGraph Orchestration & Interrupts ===")
    
    # 1. Compile Graph
    checkpointer = MemorySaver()
    print("Test 1: Compiling LangGraph workflow...")
    try:
        app = compile_workflow(checkpointer)
        print("✓ Graph compiled successfully!")
    except Exception as e:
        print(f"✗ Graph compilation failed: {e}")
        return False
        
    # 2. Run initial graph (Planner)
    thread_id = "test-thread-123"
    config = {"configurable": {"thread_id": thread_id}}
    prompt = "Compare REST and gRPC performance profiles in high-throughput APIs"
    
    print(f"\nTest 2: Starting workflow with prompt: '{prompt}'")
    try:
        # Run graph. It should run planner_node and then INTERRUPT before research_node
        print("Executing initial graph run (should halt at Research Node interrupt)...")
        initial_state = {"prompt": prompt, "depth": "basic"}
        
        # In async LangGraph, we stream/invoke the graph.
        events = []
        async for event in app.astream(initial_state, config, stream_mode="values"):
            events.append(event)
            print(f"  -> State Update: Active Node Logs: {event.get('node_logs', [])[-1:]}")
            
        # Verify the graph is indeed suspended (paused at interrupt)
        state = await app.aget_state(config)
        print(f"✓ Current Graph Execution Status:")
        print(f"  Next node to execute: {state.next}")
        print(f"  Awaiting input/approval: {bool(state.next)}")
        
        assert state.next == ("research_node",), "Graph did not interrupt before research_node!"
        print("✓ Confirmed: Graph paused at Planner approval interrupt as expected.")
        
        # 3. Simulate Human Approval / Edit Plan
        print("\nTest 3: Simulating Human Plan Approval & resume...")
        # Human can modify the plan in the state or just resume
        # Let's resume the graph. Since it is interrupted, we resume by calling aupdate_state or ainvoke(None)
        # In LangGraph, to resume a thread, we pass None to inputs:
        resume_events = []
        async for event in app.astream(None, config, stream_mode="values"):
            resume_events.append(event)
            if event.get('node_logs'):
                print(f"  -> State Update: Active Node Logs: {event['node_logs'][-1:]}")
                
        # The graph will now run research -> fact check -> writer -> then INTERRUPT before reviewer_node
        final_state = await app.aget_state(config)
        print(f"✓ Post-Resume Graph Execution Status:")
        print(f"  Next node to execute: {final_state.next}")
        
        assert final_state.next == ("reviewer_node",), "Graph did not interrupt before reviewer_node!"
        print("✓ Confirmed: Graph paused at final report approval interrupt as expected.")
        
        # Let's check that a report draft was written and sources were populated
        values = final_state.values
        assert "draft_report" in values and values["draft_report"], "Draft report was not written"
        assert "sources" in values and len(values["sources"]) > 0, "No sources retrieved"
        print(f"✓ Confirmed: Draft report generated successfully. Content length: {len(values['draft_report'])} characters.")
        print(f"✓ Confirmed: {len(values['sources'])} sources mapped to state.")
        
        # 4. Final approval to finish execution
        print("\nTest 4: Simulating Human Report Approval and ending...")
        # Human approves by resuming again with no state updates
        async for event in app.astream(None, config, stream_mode="values"):
            pass
            
        end_state = await app.aget_state(config)
        print(f"✓ Finished Graph Execution Status:")
        print(f"  Next node: {end_state.next}")
        assert not end_state.next, "Graph did not complete execution (next should be empty)"
        print("✓ Confirmed: Graph executed to completion.")
        
        print("\n✓ ALL GRAPH TESTS PASSED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"✗ Integration Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_graph_test())
    sys.exit(0 if success else 1)
