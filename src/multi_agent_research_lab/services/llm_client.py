"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import time
from dataclasses import dataclass

from openai import OpenAI, APIError, Timeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_seconds: float


class LLMClient:
    """Provider-agnostic LLM client skeleton."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """Initialize LLM client with OpenAI API.
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model name (defaults to settings)
        """
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = OpenAI(api_key=self.api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Timeout, APIError))
    )
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """Return a model completion with retry and timeout.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with content, tokens, cost, and latency
            
        Raises:
            Timeout: If API call times out after retries
            APIError: If API returns error after retries
        """
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30.0  # 30 second timeout per call
        )
        
        latency = time.time() - start_time
        
        # Calculate cost based on gpt-4o-mini pricing
        # Input: $0.15 / 1M tokens, Output: $0.60 / 1M tokens
        input_cost = response.usage.prompt_tokens * 0.15 / 1_000_000
        output_cost = response.usage.completion_tokens * 0.60 / 1_000_000
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            cost_usd=input_cost + output_cost,
            latency_seconds=latency
        )
