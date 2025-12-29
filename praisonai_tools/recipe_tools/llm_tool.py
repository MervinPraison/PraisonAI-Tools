"""
LLM Tool - Unified LLM interface for all recipes.

Provides a consistent interface for interacting with various LLM providers
(OpenAI, Anthropic, Google, etc.) with streaming, JSON schema outputs,
and prompt versioning support.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union, Generator

try:
    from .base import RecipeToolBase, RecipeToolResult, DependencyError
except ImportError:
    from base import RecipeToolBase, RecipeToolResult, DependencyError

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse(RecipeToolResult):
    """Result from LLM completion."""
    content: str = ""
    model: str = ""
    provider: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class LLMMessage:
    """A message in a conversation."""
    role: str  # system, user, assistant
    content: str


class LLMTool(RecipeToolBase):
    """Unified LLM interface supporting multiple providers."""
    
    SUPPORTED_PROVIDERS = ["openai", "anthropic", "google", "ollama"]
    
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.provider = provider.lower()
        self.model = model or self._default_model()
        self.api_key = api_key or self._get_api_key()
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
    
    def _default_model(self) -> str:
        """Get default model for provider."""
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
            "google": "gemini-1.5-flash",
            "ollama": "llama3.2",
        }
        return defaults.get(self.provider, "gpt-4o-mini")
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_var = env_vars.get(self.provider)
        return os.environ.get(env_var) if env_var else None
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        deps = {}
        
        if self.provider == "openai":
            try:
                import openai
                deps["openai"] = True
            except ImportError:
                deps["openai"] = False
        
        elif self.provider == "anthropic":
            try:
                import anthropic
                deps["anthropic"] = True
            except ImportError:
                deps["anthropic"] = False
        
        elif self.provider == "google":
            try:
                import google.generativeai
                deps["google-generativeai"] = True
            except ImportError:
                deps["google-generativeai"] = False
        
        # Check API key
        deps["api_key"] = bool(self.api_key) or self.provider == "ollama"
        
        return deps
    
    def _get_client(self):
        """Get or create the LLM client."""
        if self._client is not None:
            return self._client
        
        if self.provider == "openai":
            import openai
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        elif self.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        elif self.provider == "ollama":
            import openai
            self._client = openai.OpenAI(
                api_key="ollama",
                base_url=self.base_url or "http://localhost:11434/v1",
            )
        
        return self._client
    
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        messages: Optional[List[LLMMessage]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt
            system: Optional system message
            messages: Optional conversation history
            temperature: Override default temperature
            max_tokens: Override default max tokens
            json_schema: Optional JSON schema for structured output
            seed: Optional seed for reproducibility
            
        Returns:
            LLMResponse with the completion
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        # Build messages
        msg_list = []
        if system:
            msg_list.append({"role": "system", "content": system})
        if messages:
            for m in messages:
                msg_list.append({"role": m.role, "content": m.content})
        msg_list.append({"role": "user", "content": prompt})
        
        client = self._get_client()
        
        if self.provider in ["openai", "ollama"]:
            return self._complete_openai(client, msg_list, temp, max_tok, json_schema, seed)
        elif self.provider == "anthropic":
            return self._complete_anthropic(client, msg_list, temp, max_tok, system)
        elif self.provider == "google":
            return self._complete_google(client, prompt, temp, max_tok)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _complete_openai(
        self,
        client,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        json_schema: Optional[Dict] = None,
        seed: Optional[int] = None,
    ) -> LLMResponse:
        """Complete using OpenAI-compatible API."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if seed is not None:
            kwargs["seed"] = seed
        
        if json_schema:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            success=True,
            content=response.choices[0].message.content,
            model=response.model,
            provider=self.provider,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )
    
    def _complete_anthropic(
        self,
        client,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Complete using Anthropic API."""
        # Filter out system message and use it separately
        filtered_messages = [m for m in messages if m["role"] != "system"]
        
        kwargs = {
            "model": self.model,
            "messages": filtered_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system:
            kwargs["system"] = system
        
        response = client.messages.create(**kwargs)
        
        return LLMResponse(
            success=True,
            content=response.content[0].text,
            model=response.model,
            provider=self.provider,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )
    
    def _complete_google(
        self,
        client,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Complete using Google Generative AI."""
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        response = client.generate_content(
            prompt,
            generation_config=generation_config,
        )
        
        return LLMResponse(
            success=True,
            content=response.text,
            model=self.model,
            provider=self.provider,
            usage={},
            finish_reason="stop",
        )
    
    def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """
        Stream a completion from the LLM.
        
        Yields chunks of the response as they arrive.
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        client = self._get_client()
        
        if self.provider in ["openai", "ollama"]:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                stream=True,
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        elif self.provider == "anthropic":
            with client.messages.stream(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        
        elif self.provider == "google":
            response = client.generate_content(
                prompt,
                generation_config={"temperature": temp, "max_output_tokens": max_tok},
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
    
    def extract_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract structured JSON from LLM response.
        
        Args:
            prompt: The prompt describing what to extract
            schema: JSON schema describing expected output
            system: Optional system message
            
        Returns:
            Parsed JSON dictionary
        """
        schema_str = json.dumps(schema, indent=2)
        enhanced_prompt = f"""{prompt}

Respond with valid JSON matching this schema:
{schema_str}

Output only the JSON, no other text."""
        
        response = self.complete(
            prompt=enhanced_prompt,
            system=system or "You are a helpful assistant that outputs valid JSON.",
            json_schema=schema,
        )
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON from response: {response.content[:200]}")


# Convenience functions
def llm_complete(
    prompt: str,
    provider: str = "openai",
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Quick completion with default settings."""
    tool = LLMTool(provider=provider, model=model, temperature=temperature, max_tokens=max_tokens)
    response = tool.complete(prompt, system=system)
    return response.content


def llm_extract_json(
    prompt: str,
    schema: Dict[str, Any],
    provider: str = "openai",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Quick JSON extraction."""
    tool = LLMTool(provider=provider, model=model)
    return tool.extract_json(prompt, schema)


__all__ = [
    "LLMTool",
    "LLMResponse",
    "LLMMessage",
    "llm_complete",
    "llm_extract_json",
]
