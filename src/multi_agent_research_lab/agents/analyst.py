"""Analyst agent skeleton."""

import time

from langfuse import observe

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient):
        """Initialize Analyst agent with LLM client.
        
        Args:
            llm_client: LLM client for analysis
        """
        self.llm_client = llm_client

    @observe(name="analyst_agent", as_type="span")
    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.
        
        Steps:
        1. Read research_notes and sources
        2. Analyze using LLM: compare viewpoints, assess credibility
        3. Update state with analysis_notes
        """
        start_time = time.time()
        
        try:
            if not state.research_notes:
                state.errors.append("Analyst: No research notes to analyze")
                state.analysis_notes = "No research notes available for analysis."
                return state
            
            # Prepare sources summary
            sources_summary = "\n".join([
                f"- {s.title} ({s.url})"
                for s in state.sources
            ]) if state.sources else "No sources available"
            
            system_prompt = "You are a critical analyst. Evaluate information objectively and identify strengths and weaknesses."
            user_prompt = f"""Analyze the following research notes and sources:

Research Notes:
{state.research_notes}

Sources:
{sources_summary}

Provide a critical analysis that:
1. Compares different viewpoints if any exist
2. Assesses the credibility and quality of sources
3. Identifies any weak evidence or gaps in the research
4. Highlights key insights and patterns
5. Notes any potential biases or limitations

Be thorough and objective in your analysis."""
            
            # Call LLM with Langfuse tracing
            from langfuse import get_client
            langfuse_client = get_client()
            
            # Create a generation span for the LLM call
            with langfuse_client.start_as_current_observation(
                name="analyze_research",
                as_type="generation",
                input={"system": system_prompt, "user": user_prompt},
                model="gpt-4o-mini"
            ) as generation_span:
                llm_response = self.llm_client.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=1500
                )
                
                # Update generation span with output, usage, and cost
                generation_span.update(
                    output=llm_response.content,
                    usage_details={
                        "input": llm_response.input_tokens,
                        "output": llm_response.output_tokens,
                        "total": llm_response.input_tokens + llm_response.output_tokens
                    },
                    cost_details={
                        "total": llm_response.cost_usd
                    }
                )
            
            state.analysis_notes = llm_response.content
            
            # Record metadata
            state.agent_results.append(AgentResult(
                agent=AgentName.ANALYST,
                content=state.analysis_notes,
                metadata={
                    "num_sources_analyzed": len(state.sources),
                    "input_tokens": llm_response.input_tokens,
                    "output_tokens": llm_response.output_tokens,
                    "cost_usd": llm_response.cost_usd,
                    "latency_seconds": time.time() - start_time
                }
            ))
            
        except Exception as e:
            state.errors.append(f"Analyst failed: {str(e)}")
            state.analysis_notes = "Analysis failed due to error."
        
        return state
