"""Quick test file for multi-agent workflow."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from langfuse import get_client

from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.tracing import get_tracer

# Your test query here
TEST_QUERY = "What is GraphRAG and how does it work?"

def main():
    print("=" * 80)
    print("MULTI-AGENT RESEARCH SYSTEM TEST")
    print("=" * 80)
    print(f"\nQuery: {TEST_QUERY}\n")
    
    # Initialize tracer to check Langfuse connection
    tracer = get_tracer()
    if tracer.enabled:
        print("✓ Langfuse tracing is ENABLED")
    else:
        print("✗ Langfuse tracing is DISABLED (check your .env file)")
    
    print("\nStarting workflow...\n")
    
    # Create initial state
    request = ResearchQuery(query=TEST_QUERY, max_sources=3)
    state = ResearchState(request=request)
    
    # Run workflow
    workflow = MultiAgentWorkflow()
    result = workflow.run(state)
    
    # CRITICAL: Flush Langfuse to send all traces to the server
    # The @observe decorator batches spans and sends them asynchronously
    # We need to flush to ensure all data is sent before the program exits
    langfuse_client = get_client()
    if langfuse_client:
        print("\nFlushing traces to Langfuse...")
        langfuse_client.flush()
        print("✓ Traces flushed successfully")
    
    # Display results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    print(f"\n✓ Iterations: {result.iteration}")
    print(f"✓ Route history: {' → '.join(result.route_history)}")
    print(f"✓ Sources found: {len(result.sources)}")
    
    if result.sources:
        print("\nSources:")
        for i, source in enumerate(result.sources, 1):
            print(f"  [{i}] {source.title}")
            print(f"      {source.url}")
    
    print(f"\n✓ Research notes length: {len(result.research_notes or '')} chars")
    print(f"✓ Analysis notes length: {len(result.analysis_notes or '')} chars")
    print(f"✓ Final answer length: {len(result.final_answer or '')} chars")
    
    # Calculate metrics
    total_tokens = sum(
        r.metadata.get("input_tokens", 0) + r.metadata.get("output_tokens", 0)
        for r in result.agent_results
    )
    total_cost = sum(
        r.metadata.get("cost_usd", 0.0)
        for r in result.agent_results
    )
    
    print(f"\n✓ Total tokens used: {total_tokens}")
    print(f"✓ Total cost: ${total_cost:.4f}")
    
    if result.errors:
        print(f"\n⚠ Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")
    
    print("\n" + "=" * 80)
    print("FINAL ANSWER")
    print("=" * 80)
    print(f"\n{result.final_answer}\n")
    
    # Trace info
    print("=" * 80)
    print("TRACING INFO")
    print("=" * 80)
    
    # Get trace ID from result state
    if tracer.enabled and result.trace_id:
        trace_url = tracer.get_trace_url(result.trace_id)
        print(f"\n✓ Trace ID: {result.trace_id}")
        print(f"✓ Trace URL: {trace_url}")
        print("\nOpen the URL above in your browser to view the trace on Langfuse!")
    else:
        print("\n✗ Tracing not enabled or no trace ID captured")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
