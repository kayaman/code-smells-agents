#!/usr/bin/env python3
"""
Databricks Model Serving client for code review agents.
Handles authentication, request formatting, and response parsing.
"""

import json
import time
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class DatabricksModelClient:
    """Client for Databricks Model Serving endpoints."""
    
    def __init__(
        self,
        host: str,
        token: str,
        endpoint: str,
        timeout: int = 120,
        max_retries: int = 3
    ):
        """
        Initialize the Databricks client.
        
        Args:
            host: Databricks workspace URL (e.g., https://xxx.cloud.databricks.com)
            token: Databricks PAT or service principal token
            endpoint: Model serving endpoint name
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.host = host.rstrip('/')
        self.token = token
        self.endpoint = endpoint
        self.timeout = timeout
        
        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    @property
    def endpoint_url(self) -> str:
        """Get the full endpoint URL."""
        return f"{self.host}/serving-endpoints/{self.endpoint}/invocations"
    
    @property
    def headers(self) -> dict:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def query(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        stop_sequences: Optional[list[str]] = None
    ) -> str:
        """
        Send a query to the model serving endpoint.
        
        Supports multiple model formats:
        - OpenAI-compatible (messages format)
        - Legacy completion format
        - Foundation Model APIs
        
        Args:
            system_prompt: System instructions for the model
            user_message: User query/content to analyze
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            stop_sequences: Optional stop sequences
        
        Returns:
            Model response text
        """
        
        # Try OpenAI-compatible format first (most common for chat models)
        payload = self._build_chat_payload(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences
        )
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                self.endpoint_url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            elapsed = time.time() - start_time
            print(f"Model response received in {elapsed:.2f}s")
            
            response.raise_for_status()
            
            return self._parse_response(response.json())
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                # Try legacy format
                print("Retrying with legacy completion format...")
                payload = self._build_completion_payload(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                response = self.session.post(
                    self.endpoint_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return self._parse_response(response.json())
            raise
    
    def _build_chat_payload(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: Optional[list[str]] = None
    ) -> dict:
        """Build OpenAI-compatible chat completion payload."""
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if stop_sequences:
            payload["stop"] = stop_sequences
        
        return payload
    
    def _build_completion_payload(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int
    ) -> dict:
        """Build legacy completion format payload."""
        # Combine system and user into single prompt
        full_prompt = f"""### System Instructions:
{system_prompt}

### User Request:
{user_message}

### Response:
"""
        return {
            "prompt": full_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
    
    def _parse_response(self, response_data: dict) -> str:
        """
        Parse response from various model serving formats.
        
        Handles:
        - OpenAI format: {"choices": [{"message": {"content": "..."}}]}
        - Completion format: {"choices": [{"text": "..."}]}
        - Direct format: {"predictions": ["..."]} or {"output": "..."}
        """
        
        # OpenAI chat format
        if "choices" in response_data:
            choices = response_data["choices"]
            if choices and isinstance(choices, list):
                choice = choices[0]
                
                # Chat completion format
                if "message" in choice:
                    return choice["message"].get("content", "")
                
                # Legacy completion format
                if "text" in choice:
                    return choice["text"]
        
        # Foundation Model API format
        if "predictions" in response_data:
            predictions = response_data["predictions"]
            if predictions and isinstance(predictions, list):
                return predictions[0]
        
        # Direct output format
        if "output" in response_data:
            return response_data["output"]
        
        # Databricks custom format
        if "generated_text" in response_data:
            return response_data["generated_text"]
        
        # Fallback: return full response as string
        print(f"Warning: Unknown response format, returning raw: {list(response_data.keys())}")
        return json.dumps(response_data)
    
    def health_check(self) -> bool:
        """Check if the endpoint is healthy and responding."""
        try:
            # Most endpoints support a simple query
            response = self.query(
                system_prompt="You are a helpful assistant.",
                user_message="Say 'OK' if you're working.",
                max_tokens=10
            )
            return "OK" in response.upper() or len(response) > 0
        except Exception as e:
            print(f"Health check failed: {e}")
            return False


class MockDatabricksClient(DatabricksModelClient):
    """Mock client for testing without hitting real endpoints."""
    
    def __init__(self, *args, **kwargs):
        # Don't call parent init to avoid needing real credentials
        self.mock_responses = []
        self._response_index = 0
    
    def add_mock_response(self, response: str):
        """Add a mock response to the queue."""
        self.mock_responses.append(response)
    
    def query(self, **kwargs) -> str:
        """Return mock response."""
        if self.mock_responses:
            response = self.mock_responses[self._response_index % len(self.mock_responses)]
            self._response_index += 1
            return response
        
        # Default mock response
        return json.dumps({
            "summary": "Mock analysis complete",
            "violations": [],
            "passed_checks": ["MOCK-001"],
            "recommendations": [],
            "metrics": {"files_analyzed": 1, "total_lines": 10}
        })


# Example usage and testing
if __name__ == "__main__":
    import os
    
    # Test with real endpoint
    host = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    endpoint = os.environ.get("DATABRICKS_ENDPOINT", "code-review-v1")
    
    if host and token:
        client = DatabricksModelClient(host=host, token=token, endpoint=endpoint)
        
        print("Testing endpoint health...")
        if client.health_check():
            print("✅ Endpoint is healthy")
            
            # Test a simple code review query
            result = client.query(
                system_prompt="You are a code reviewer. Respond with JSON.",
                user_message='Review this Python code:\n```python\ndef foo(x): return x+1\n```',
                temperature=0.1,
                max_tokens=500
            )
            print(f"Response: {result[:200]}...")
        else:
            print("❌ Endpoint health check failed")
    else:
        print("No credentials provided, testing mock client...")
        mock = MockDatabricksClient()
        result = mock.query(system_prompt="test", user_message="test")
        print(f"Mock response: {result}")
