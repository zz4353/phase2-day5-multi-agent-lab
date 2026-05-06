"""Supervisor / router skeleton."""

from langfuse import observe

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    @observe(name="supervisor_agent")
    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.
        
        Routing policy:
        - researcher: if research_notes is None
        - analyst: if research_notes exists but analysis_notes is None
        - writer: if analysis_notes exists but final_answer is None
        - done: if final_answer exists OR max_iterations reached
        """
        settings = get_settings()
        
        # Guardrail: Check max iterations
        if state.iteration >= settings.max_iterations:
            state.errors.append(f"Max iterations ({settings.max_iterations}) reached")
            state.record_route("done")
            return state
        
        # Decide route based on what's missing
        if state.final_answer is not None:
            route = "done"
        elif state.research_notes is None:
            route = "researcher"
        elif state.analysis_notes is None:
            route = "analyst"
        elif state.final_answer is None:
            route = "writer"
        else:
            # Should not reach here, but fallback to done
            route = "done"
        
        # Record the routing decision
        state.record_route(route)
        
        return state
