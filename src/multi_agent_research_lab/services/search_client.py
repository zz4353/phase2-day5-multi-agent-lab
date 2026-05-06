"""Search client abstraction for ResearcherAgent."""

from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchError(Exception):
    """Raised when search fails after retries."""
    pass


class SearchClient:
    """Provider-agnostic search client skeleton."""

    def __init__(self, api_key: str | None = None):
        """Initialize Search client with Tavily API.
        
        Args:
            api_key: Tavily API key (defaults to settings)
            
        Raises:
            ValueError: If TAVILY_API_KEY not configured
        """
        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key
        
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not configured")
        
        self.client = TavilyClient(api_key=self.api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents using Tavily API with retry and timeout.
        
        Args:
            query: Search query
            max_results: Maximum number of results (1-20)
            
        Returns:
            List of SourceDocument with title, url, snippet
            
        Raises:
            SearchError: If search fails after retries
        """
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_raw_content=False
            )
            
            sources = []
            for result in response.get("results", []):
                sources.append(SourceDocument(
                    title=result.get("title", "Untitled"),
                    url=result.get("url"),
                    snippet=result.get("content", ""),
                    metadata={
                        "score": result.get("score", 0.0),
                        "published_date": result.get("published_date")
                    }
                ))
            
            return sources
            
        except Exception as e:
            raise SearchError(f"Tavily search failed: {str(e)}") from e
