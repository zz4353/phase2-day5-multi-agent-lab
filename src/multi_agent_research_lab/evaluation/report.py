"""Benchmark report rendering."""

from datetime import datetime
from typing import List

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(
    metrics: list[BenchmarkMetrics],
    queries: List[str] | None = None
) -> str:
    """Render benchmark metrics to markdown with rich analysis.
    
    Args:
        metrics: List of benchmark metrics
        queries: Optional list of queries used for benchmarking
        
    Returns:
        Markdown formatted report
    """
    lines = [
        "# Benchmark Report: Single-Agent vs Multi-Agent",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        ""
    ]
    
    # Calculate averages for each run type
    baseline_metrics = [m for m in metrics if "baseline" in m.run_name.lower()]
    multi_metrics = [m for m in metrics if "multi" in m.run_name.lower()]
    
    if baseline_metrics and multi_metrics:
        avg_baseline_latency = sum(m.latency_seconds for m in baseline_metrics) / len(baseline_metrics)
        avg_multi_latency = sum(m.latency_seconds for m in multi_metrics) / len(multi_metrics)
        
        avg_baseline_cost = sum(m.estimated_cost_usd or 0 for m in baseline_metrics) / len(baseline_metrics)
        avg_multi_cost = sum(m.estimated_cost_usd or 0 for m in multi_metrics) / len(multi_metrics)
        
        avg_baseline_quality = sum(m.quality_score or 0 for m in baseline_metrics) / len(baseline_metrics)
        avg_multi_quality = sum(m.quality_score or 0 for m in multi_metrics) / len(multi_metrics)
        
        lines.extend([
            "| Metric | Single-Agent | Multi-Agent | Winner |",
            "|---|---:|---:|---|",
            f"| Avg Latency (s) | {avg_baseline_latency:.2f} | {avg_multi_latency:.2f} | {'✓ Single' if avg_baseline_latency < avg_multi_latency else '✓ Multi'} |",
            f"| Avg Cost ($) | {avg_baseline_cost:.4f} | {avg_multi_cost:.4f} | {'✓ Single' if avg_baseline_cost < avg_multi_cost else '✓ Multi'} |",
            f"| Avg Quality (0-10) | {avg_baseline_quality:.1f} | {avg_multi_quality:.1f} | {'✓ Single' if avg_baseline_quality > avg_multi_quality else '✓ Multi'} |",
            "",
            "## Detailed Results",
            ""
        ])
    
    # Detailed table
    lines.extend([
        "| Run | Latency (s) | Cost ($) | Quality (0-10) | Notes |",
        "|---|---:|---:|---:|---|"
    ])
    
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |"
        )
    
    # Add queries section if provided
    if queries:
        lines.extend([
            "",
            "## Test Queries",
            ""
        ])
        for i, query in enumerate(queries, 1):
            lines.append(f"{i}. {query}")
    
    # Add analysis section
    lines.extend([
        "",
        "## Analysis",
        ""
    ])
    
    if baseline_metrics and multi_metrics:
        # Latency analysis
        if avg_multi_latency > avg_baseline_latency:
            latency_diff = ((avg_multi_latency - avg_baseline_latency) / avg_baseline_latency) * 100
            lines.append(f"- **Latency**: Multi-agent is {latency_diff:.1f}% slower due to multiple LLM calls and routing overhead.")
        else:
            lines.append(f"- **Latency**: Multi-agent is comparable or faster than single-agent.")
        
        # Cost analysis
        if avg_multi_cost > avg_baseline_cost:
            cost_diff = ((avg_multi_cost - avg_baseline_cost) / avg_baseline_cost) * 100
            lines.append(f"- **Cost**: Multi-agent is {cost_diff:.1f}% more expensive due to additional LLM calls.")
        else:
            lines.append(f"- **Cost**: Multi-agent has comparable cost to single-agent.")
        
        # Quality analysis
        if avg_multi_quality > avg_baseline_quality:
            quality_diff = avg_multi_quality - avg_baseline_quality
            lines.append(f"- **Quality**: Multi-agent scores {quality_diff:.1f} points higher due to specialized agents and better analysis.")
        else:
            lines.append(f"- **Quality**: Single-agent has comparable or better quality.")
    
    lines.extend([
        "",
        "## Recommendations",
        "",
        "- **Use Multi-Agent when**: Quality and depth of analysis are more important than speed/cost",
        "- **Use Single-Agent when**: Speed and cost efficiency are priorities",
        "- **Consider**: The tradeoff between quality and latency/cost for your specific use case",
        ""
    ])
    
    return "\n".join(lines) + "\n"
