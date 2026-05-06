"""Benchmark skeleton for single-agent vs multi-agent."""

import re
from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState


Runner = Callable[[str], ResearchState]


def calculate_citation_coverage(final_answer: str, num_sources: int) -> float:
    """Calculate citation coverage as percentage of sources cited.
    
    Args:
        final_answer: The final answer text
        num_sources: Number of sources available
        
    Returns:
        Citation coverage as percentage (0-100)
    """
    if not final_answer or num_sources == 0:
        return 0.0
    
    # Find all citations like [1], [2], etc.
    citations = set(re.findall(r'\[(\d+)\]', final_answer))
    cited_sources = len([c for c in citations if int(c) <= num_sources])
    
    return (cited_sources / num_sources) * 100.0


def calculate_quality_score(state: ResearchState) -> float:
    """Calculate quality score based on multiple factors.
    
    Scoring rubric (0-10):
    - Has final answer: 2 points
    - Has sources: 2 points
    - Has research notes: 2 points
    - Has analysis notes: 2 points
    - Has citations: 2 points
    - No errors: bonus 1 point (max 10)
    
    Args:
        state: ResearchState after workflow completion
        
    Returns:
        Quality score from 0-10
    """
    score = 0.0
    
    # Has final answer
    if state.final_answer and len(state.final_answer) > 50:
        score += 2.0
    
    # Has sources
    if len(state.sources) > 0:
        score += 2.0
    
    # Has research notes
    if state.research_notes and len(state.research_notes) > 50:
        score += 2.0
    
    # Has analysis notes (only for multi-agent)
    if state.analysis_notes and len(state.analysis_notes) > 50:
        score += 2.0
    
    # Has citations
    if state.final_answer and '[' in state.final_answer:
        score += 2.0
    
    # No errors bonus
    if len(state.errors) == 0:
        score = min(10.0, score + 1.0)
    
    return score


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency and return comprehensive metrics.
    
    Args:
        run_name: Name of the benchmark run
        query: Research query
        runner: Function that runs the workflow and returns ResearchState
        
    Returns:
        Tuple of (final state, benchmark metrics)
    """
    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    
    # Calculate total cost from agent results
    total_cost = sum(
        r.metadata.get("cost_usd", 0.0)
        for r in state.agent_results
    )
    
    # Calculate quality score
    quality = calculate_quality_score(state)
    
    # Calculate citation coverage
    citation_coverage = calculate_citation_coverage(
        state.final_answer or "",
        len(state.sources)
    )
    
    # Build notes
    notes_parts = []
    if state.errors:
        notes_parts.append(f"{len(state.errors)} errors")
    notes_parts.append(f"{citation_coverage:.0f}% citations")
    notes_parts.append(f"{len(state.sources)} sources")
    
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=total_cost if total_cost > 0 else None,
        quality_score=quality,
        notes=", ".join(notes_parts)
    )
    
    return state, metrics
