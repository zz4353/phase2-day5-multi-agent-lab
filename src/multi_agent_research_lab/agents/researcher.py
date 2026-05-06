"""Researcher agent skeleton."""

import time

from langfuse import observe

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient, SearchError


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, llm_client: LLMClient, search_client: SearchClient):
        """Initialize Researcher agent with LLM and Search clients.
        
        Args:
            llm_client: LLM client for summarization
            search_client: Search client for finding sources
        """
        self.llm_client = llm_client
        self.search_client = search_client

    @observe(name="researcher_agent", as_type="span")
    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.
        
        Steps:
        1. Search for sources using Tavily
        2. Summarize sources using LLM
        3. Update state with sources and research_notes
        """
        start_time = time.time()
        
        try:
            # Step 1: Search for sources
            sources = self.search_client.search(
                query=state.request.query,
                max_results=state.request.max_sources
            )
            state.sources = sources
            
            # Step 2: Summarize sources if found
            if sources:
                sources_text = "\n\n".join([
                    f"Source {i+1}: {s.title}\nURL: {s.url}\n{s.snippet}"
                    for i, s in enumerate(sources)
                ])
                
                system_prompt = "You are a research assistant. Summarize information accurately and comprehensively."
                user_prompt = f"""Based on the following sources, create a comprehensive research summary for the query: "{state.request.query}"

Sources:
{sources_text}

Provide a detailed summary that captures key information from all sources. Be factual and cite which sources support each point."""
                
                # Call LLM with Langfuse tracing
                from langfuse import get_client
                langfuse_client = get_client()
                
                # Create a generation span for the LLM call
                with langfuse_client.start_as_current_observation(
                    name="summarize_sources",
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
                            "input_tokens": llm_response.input_tokens,
                            "output_tokens": llm_response.output_tokens,
                            "total_tokens": llm_response.input_tokens + llm_response.output_tokens
                        },
                        cost_details={
                            "total_cost": llm_response.cost_usd
                        }
                    )
                
                state.research_notes = llm_response.content
                
                # Record metadata
                state.agent_results.append(AgentResult(
                    agent=AgentName.RESEARCHER,
                    content=state.research_notes,
                    metadata={
                        "num_sources": len(sources),
                        "input_tokens": llm_response.input_tokens,
                        "output_tokens": llm_response.output_tokens,
                        "cost_usd": llm_response.cost_usd,
                        "latency_seconds": time.time() - start_time
                    }
                ))
            else:
                state.research_notes = "No sources found for the query."
                state.errors.append("Researcher: No sources found")
                
        except SearchError as e:
            state.errors.append(f"Researcher search failed: {str(e)}")
            state.research_notes = "Research failed due to search error."
        except Exception as e:
            state.errors.append(f"Researcher failed: {str(e)}")
            state.research_notes = "Research failed due to unexpected error."
        
        return state
