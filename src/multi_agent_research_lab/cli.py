"""Command-line entrypoint for the lab starter."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline for comparison with multi-agent."""
    import time
    
    _init()
    
    from multi_agent_research_lab.services.llm_client import LLMClient
    from multi_agent_research_lab.services.search_client import SearchClient
    from multi_agent_research_lab.observability.tracing import trace_span
    
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    
    start_time = time.time()
    
    try:
        with trace_span("baseline_single_agent", {"query": query}) as span:
            # Initialize clients
            llm_client = LLMClient()
            search_client = SearchClient()
            
            # Step 1: Search for sources
            console.print("[yellow]Searching for sources...[/yellow]")
            sources = search_client.search(query=query, max_results=request.max_sources)
            state.sources = sources
            
            # Step 2: Create single comprehensive prompt
            sources_text = "\n\n".join([
                f"Source {i+1}: {s.title}\nURL: {s.url}\n{s.snippet}"
                for i, s in enumerate(sources)
            ]) if sources else "No sources found"
            
            sources_with_urls = "\n".join([
                f"[{i+1}] {s.title}: {s.url}"
                for i, s in enumerate(sources)
            ]) if sources else "No sources available"
            
            console.print("[yellow]Generating response...[/yellow]")
            
            # Single LLM call to do everything
            system_prompt = "You are a research assistant. Research, analyze, and write a comprehensive answer with citations."
            user_prompt = f"""Research Query: "{query}"

Sources Found:
{sources_text}

Task: Based on the sources above, provide a comprehensive answer that:
1. Summarizes key information from the sources
2. Analyzes and compares different viewpoints if any
3. Writes a clear, well-structured answer for {request.audience}
4. Includes citations using [1], [2], etc. format

Sources for citations:
{sources_with_urls}

Write your comprehensive answer now:"""
            
            llm_response = llm_client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=3000
            )
            
            state.final_answer = llm_response.content
            
            # Calculate metrics
            latency = time.time() - start_time
            
            # Display results
            console.print(Panel.fit(
                f"[green]✓[/green] Completed in {latency:.2f}s\n"
                f"[green]✓[/green] Sources found: {len(sources)}\n"
                f"[green]✓[/green] Tokens used: {llm_response.input_tokens + llm_response.output_tokens}\n"
                f"[green]✓[/green] Cost: ${llm_response.cost_usd:.4f}\n"
                f"[green]✓[/green] Trace URL: {span.get('trace_url', 'N/A')}",
                title="Baseline Metrics"
            ))
            console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline Answer"))
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1) from e


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""
    import time
    
    _init()
    
    from multi_agent_research_lab.observability.tracing import trace_span
    
    start_time = time.time()
    
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    
    try:
        with trace_span("multi_agent_workflow", {"query": query}) as span:
            console.print("[yellow]Running multi-agent workflow...[/yellow]")
            result = workflow.run(state)
            
            # Calculate metrics
            latency = time.time() - start_time
            total_tokens = sum(
                r.metadata.get("input_tokens", 0) + r.metadata.get("output_tokens", 0)
                for r in result.agent_results
            )
            total_cost = sum(
                r.metadata.get("cost_usd", 0.0)
                for r in result.agent_results
            )
            
            # Display results
            console.print(Panel.fit(
                f"[green]✓[/green] Completed in {latency:.2f}s\n"
                f"[green]✓[/green] Iterations: {result.iteration}\n"
                f"[green]✓[/green] Sources found: {len(result.sources)}\n"
                f"[green]✓[/green] Tokens used: {total_tokens}\n"
                f"[green]✓[/green] Cost: ${total_cost:.4f}\n"
                f"[green]✓[/green] Errors: {len(result.errors)}\n"
                f"[green]✓[/green] Trace URL: {span.get('trace_url', 'N/A')}",
                title="Multi-Agent Metrics"
            ))
            
            if result.errors:
                console.print(Panel.fit(
                    "\n".join(result.errors),
                    title="[yellow]Errors[/yellow]"
                ))
            
            console.print(Panel.fit(
                result.final_answer or "No final answer generated",
                title="Multi-Agent Answer"
            ))
            
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()


@app.command()
def benchmark(
    queries: Annotated[
        list[str],
        typer.Option("--query", "-q", help="Research queries to benchmark (can specify multiple)")
    ] = None,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output file for benchmark report")
    ] = "reports/benchmark_report.md",
) -> None:
    """Run benchmark comparing single-agent vs multi-agent."""
    import time
    from pathlib import Path
    
    _init()
    
    from multi_agent_research_lab.services.llm_client import LLMClient
    from multi_agent_research_lab.services.search_client import SearchClient
    
    # Default queries if none provided
    if not queries:
        queries = [
            "Research GraphRAG state-of-the-art and write a 500-word summary",
            "Compare transformer architectures: BERT vs GPT vs T5",
            "Explain quantum computing applications in cryptography"
        ]
    
    console.print(f"[yellow]Running benchmark with {len(queries)} queries...[/yellow]")
    
    all_metrics = []
    
    for i, query in enumerate(queries, 1):
        console.print(f"\n[cyan]Query {i}/{len(queries)}:[/cyan] {query[:80]}...")
        
        # Run baseline
        console.print("[yellow]  Running single-agent baseline...[/yellow]")
        
        def baseline_runner(q: str) -> ResearchState:
            llm_client = LLMClient()
            search_client = SearchClient()
            request = ResearchQuery(query=q)
            state = ResearchState(request=request)
            
            sources = search_client.search(query=q, max_results=request.max_sources)
            state.sources = sources
            
            sources_text = "\n\n".join([
                f"Source {i+1}: {s.title}\nURL: {s.url}\n{s.snippet}"
                for i, s in enumerate(sources)
            ]) if sources else "No sources found"
            
            sources_with_urls = "\n".join([
                f"[{i+1}] {s.title}: {s.url}"
                for i, s in enumerate(sources)
            ]) if sources else "No sources available"
            
            system_prompt = "You are a research assistant. Research, analyze, and write a comprehensive answer with citations."
            user_prompt = f"""Research Query: "{q}"

Sources Found:
{sources_text}

Task: Based on the sources above, provide a comprehensive answer that:
1. Summarizes key information from the sources
2. Analyzes and compares different viewpoints if any
3. Writes a clear, well-structured answer for {request.audience}
4. Includes citations using [1], [2], etc. format

Sources for citations:
{sources_with_urls}

Write your comprehensive answer now:"""
            
            llm_response = llm_client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=3000
            )
            
            state.final_answer = llm_response.content
            from multi_agent_research_lab.core.schemas import AgentName, AgentResult
            state.agent_results.append(AgentResult(
                agent=AgentName.WRITER,
                content=llm_response.content,
                metadata={
                    "input_tokens": llm_response.input_tokens,
                    "output_tokens": llm_response.output_tokens,
                    "cost_usd": llm_response.cost_usd
                }
            ))
            
            return state
        
        baseline_state, baseline_metrics = run_benchmark(
            f"baseline_q{i}",
            query,
            baseline_runner
        )
        all_metrics.append(baseline_metrics)
        console.print(f"    ✓ Latency: {baseline_metrics.latency_seconds:.2f}s, "
                     f"Quality: {baseline_metrics.quality_score:.1f}/10")
        
        # Run multi-agent
        console.print("[yellow]  Running multi-agent workflow...[/yellow]")
        
        def multi_agent_runner(q: str) -> ResearchState:
            state = ResearchState(request=ResearchQuery(query=q))
            workflow = MultiAgentWorkflow()
            return workflow.run(state)
        
        multi_state, multi_metrics = run_benchmark(
            f"multi_agent_q{i}",
            query,
            multi_agent_runner
        )
        all_metrics.append(multi_metrics)
        console.print(f"    ✓ Latency: {multi_metrics.latency_seconds:.2f}s, "
                     f"Quality: {multi_metrics.quality_score:.1f}/10")
    
    # Generate report
    console.print(f"\n[yellow]Generating benchmark report...[/yellow]")
    report = render_markdown_report(all_metrics, queries)
    
    # Save report
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    
    console.print(f"[green]✓[/green] Benchmark report saved to: {output}")
    console.print(f"\n[cyan]Preview:[/cyan]")
    console.print(report[:500] + "...")
