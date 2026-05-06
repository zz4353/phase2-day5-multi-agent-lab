"""Simple component test."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

print("Testing imports...")

try:
    from multi_agent_research_lab.core.config import get_settings
    print("✓ Config imported")
    
    settings = get_settings()
    print(f"✓ Settings loaded")
    print(f"  - OpenAI API key: {'SET' if settings.openai_api_key else 'NOT SET'}")
    print(f"  - Tavily API key: {'SET' if settings.tavily_api_key else 'NOT SET'}")
    print(f"  - Langfuse public key: {'SET' if settings.langfuse_public_key else 'NOT SET'}")
    print(f"  - Langfuse secret key: {'SET' if settings.langfuse_secret_key else 'NOT SET'}")
    
except Exception as e:
    print(f"✗ Config error: {e}")
    exit(1)

print("\nTesting LLM Client...")
try:
    from multi_agent_research_lab.services.llm_client import LLMClient
    print("✓ LLM Client imported")
    
    llm = LLMClient()
    print("✓ LLM Client initialized")
    
    # Test simple completion
    print("  Testing simple completion...")
    response = llm.complete(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say 'Hello, I am working!' in exactly 5 words.",
        max_tokens=50
    )
    print(f"  ✓ Response: {response.content}")
    print(f"  ✓ Tokens: {response.input_tokens + response.output_tokens}")
    print(f"  ✓ Cost: ${response.cost_usd:.6f}")
    
except Exception as e:
    print(f"✗ LLM Client error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\nTesting Search Client...")
try:
    from multi_agent_research_lab.services.search_client import SearchClient
    print("✓ Search Client imported")
    
    search = SearchClient()
    print("✓ Search Client initialized")
    
    # Test simple search
    print("  Testing simple search...")
    results = search.search("Python programming", max_results=2)
    print(f"  ✓ Found {len(results)} results")
    for i, result in enumerate(results, 1):
        print(f"    [{i}] {result.title[:60]}...")
    
except Exception as e:
    print(f"✗ Search Client error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\nTesting Langfuse Tracing...")
try:
    from multi_agent_research_lab.observability.tracing import get_tracer, trace_span
    print("✓ Tracing imported")
    
    tracer = get_tracer()
    print(f"✓ Tracer initialized (enabled: {tracer.enabled})")
    
    if tracer.enabled:
        print("  Testing trace span...")
        with trace_span("test_span", {"test": "value"}) as span:
            print(f"  ✓ Span created")
            print(f"    - Trace ID: {span.get('trace_id', 'N/A')}")
            print(f"    - Span ID: {span.get('span_id', 'N/A')}")
            if span.get('trace_url'):
                print(f"    - Trace URL: {span['trace_url']}")
    else:
        print("  ⚠ Tracing disabled (check Langfuse keys in .env)")
    
except Exception as e:
    print(f"✗ Tracing error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("ALL TESTS PASSED! ✓")
print("=" * 80)
print("\nYou can now run: python t.py")
