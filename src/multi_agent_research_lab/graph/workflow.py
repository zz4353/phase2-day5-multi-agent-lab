"""LangGraph workflow skeleton."""

from typing import Literal

from langfuse import observe
from langgraph.graph import StateGraph, END

from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self):
        """Initialize workflow with agents."""
        settings = get_settings()
        
        # Initialize clients
        llm_client = LLMClient()
        search_client = SearchClient()
        
        # Initialize agents
        self.supervisor = SupervisorAgent()
        self.researcher = ResearcherAgent(llm_client, search_client)
        self.analyst = AnalystAgent(llm_client)
        self.writer = WriterAgent(llm_client)
        
        self.graph = None

    def build(self) -> StateGraph:
        """Create a LangGraph graph.
        
        Graph structure:
        - Entry point: supervisor
        - Nodes: supervisor, researcher, analyst, writer
        - Conditional edges from supervisor based on routing decision
        - Edges from workers back to supervisor
        - Stop condition: when supervisor routes to "done"
        """
        workflow = StateGraph(ResearchState)
        
        # Add nodes
        workflow.add_node("supervisor", self.supervisor.run)
        workflow.add_node("researcher", self.researcher.run)
        workflow.add_node("analyst", self.analyst.run)
        workflow.add_node("writer", self.writer.run)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional edges from supervisor
        def route_decision(state: ResearchState) -> Literal["researcher", "analyst", "writer", "done"]:
            """Get the last routing decision from supervisor."""
            if not state.route_history:
                return "done"
            last_route = state.route_history[-1]
            if last_route in ["researcher", "analyst", "writer", "done"]:
                return last_route  # type: ignore
            return "done"
        
        workflow.add_conditional_edges(
            "supervisor",
            route_decision,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END
            }
        )
        
        # Add edges from workers back to supervisor
        workflow.add_edge("researcher", "supervisor")
        workflow.add_edge("analyst", "supervisor")
        workflow.add_edge("writer", "supervisor")
        
        self.graph = workflow.compile()
        return self.graph

    @observe(name="multi_agent_workflow")
    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state.
        
        Args:
            state: Initial ResearchState with query
            
        Returns:
            Final ResearchState after workflow completion
        """
        if self.graph is None:
            self.build()
        
        # Capture trace ID from current context
        from langfuse import get_client
        langfuse_client = get_client()
        if langfuse_client:
            trace_id = langfuse_client.get_current_trace_id()
            if trace_id:
                state.trace_id = trace_id
        
        # Invoke the graph
        result = self.graph.invoke(state)
        
        # LangGraph returns dict-like object, convert back to ResearchState
        if isinstance(result, ResearchState):
            return result
        else:
            # If result is dict, create ResearchState from it
            return ResearchState(**result)
