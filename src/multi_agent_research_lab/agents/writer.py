"""Writer agent skeleton."""

import time

from langfuse import observe

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient):
        """Initialize Writer agent with LLM client.
        
        Args:
            llm_client: LLM client for writing
        """
        self.llm_client = llm_client

    @observe(name="writer_agent", as_type="span")
    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.
        
        Steps:
        1. Read research_notes, analysis_notes, sources
        2. Write final_answer using LLM with citations
        3. Update state with final_answer
        """
        start_time = time.time()
        
        try:
            if not state.research_notes:
                state.errors.append("Writer: No research notes to write from")
                state.final_answer = "Unable to generate answer due to missing research."
                return state
            
            # Prepare sources with URLs for citations
            sources_with_urls = "\n".join([
                f"[{i+1}] {s.title}: {s.url}"
                for i, s in enumerate(state.sources)
            ]) if state.sources else "No sources available"
            
            system_prompt = "You are a technical writer. Write clear, well-cited content for the target audience."
            user_prompt = f"""Write a comprehensive answer to the query: "{state.request.query}"

Research Notes:
{state.research_notes}

Analysis Notes:
{state.analysis_notes or "No analysis available"}

Sources (for citations):
{sources_with_urls}

Requirements:
- Target audience: {state.request.audience}
- Include citations using [1], [2], etc. format
- Be clear, accurate, and well-structured
- Cite sources for all major claims
- Write in a professional but accessible tone
- Ensure the answer directly addresses the query

Write the final answer now:"""
            
            # Call LLM with Langfuse tracing
            from langfuse import get_client
            langfuse_client = get_client()
            
            # Create a generation span for the LLM call
            with langfuse_client.start_as_current_observation(
                name="write_final_answer",
                as_type="generation",
                input={"system": system_prompt, "user": user_prompt},
                model="gpt-4o-mini"
            ) as generation_span:
                llm_response = self.llm_client.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=3000
                )
                
                # Update generation span with output, usage, and cost
                generation_span.update(
                    output=llm_response.content,
                    usage_details={
                        "input_tokens": llm_response.input_tokens,
                        "output_tokens": llm_response.output_tokens,
                        "total_tokens": llm_response.input_tokens + llm_response.output_tokens
                    },
                    cost_details={
                        "total_cost": llm_response.cost_usd
                    }
                )
            
            state.final_answer = llm_response.content
            
            # Count citations (rough estimate)
            num_citations = state.final_answer.count("[") if state.final_answer else 0
            
            # Record metadata
            state.agent_results.append(AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={
                    "num_citations": num_citations,
                    "answer_length": len(state.final_answer),
                    "input_tokens": llm_response.input_tokens,
                    "output_tokens": llm_response.output_tokens,
                    "cost_usd": llm_response.cost_usd,
                    "latency_seconds": time.time() - start_time
                }
            ))
            
        except Exception as e:
            state.errors.append(f"Writer failed: {str(e)}")
            state.final_answer = "Unable to generate answer due to error."
        
        return state
