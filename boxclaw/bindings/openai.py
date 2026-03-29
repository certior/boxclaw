import functools
from typing import Any, Callable

# Standard Certior SDK sandbox
from ..sandbox import CertiorSandbox, CertiorSecurityError
from ..middlewares import CertiorClient

class CertiorOpenAIAssistantMiddleware:
    """
    A unified middleware interceptor for OpenAI's Assistant API. 
    Wraps standard OpenAI python SDK objects so arbitrary Beta assistants 
    execute locally strictly within bounded mathematical contexts.
    """
    def __init__(self, agent_id: str, certior_url: str = "http://localhost:5000", api_key: str = None):
        self.agent_id = agent_id
        self.client = CertiorClient(endpoint=certior_url, api_key=api_key)
        CertiorSandbox.initialize(secret_key=api_key)

    def wrap_run_execution(self, submit_tool_outputs_func: Callable, required_capabilities: list[str]) -> Callable:
        """
        Wraps `client.beta.threads.runs.submit_tool_outputs`. 
        When local functions are executed and passed back to OpenAI, we intercept
        the wrapper here to ensure OS bounding.
        """
        @functools.wraps(submit_tool_outputs_func)
        def secured_submit(*args, **kwargs) -> Any:
            request_hash = str(hash(str(kwargs.get('tool_outputs', []))))
            
            # Phase 9.1: Request Proof Evaluation
            signed_token = self.client.request_delegation(
                agent_id=self.agent_id,
                request_hash=request_hash,
                required_capabilities=required_capabilities
            )
            
            # Phase 9.4: Lock it down 
            with CertiorSandbox.assume_capabilities(signed_token):
                return submit_tool_outputs_func(*args, **kwargs)

        return secured_submit
