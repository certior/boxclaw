import functools
from typing import Any, Callable

from ..sandbox import CertiorSandbox, CertiorSecurityError
from ..middlewares import CertiorClient
from ..fallback import format_safe_llm_rejection

class CertiorLangChainMiddleware:
    """
    A unified middleware interceptor for LangChain. 
    Wraps standard `AgentExecutor` or `Runnable` instances so every tool execution
    is mathematically proven against the Certior engine before entering the OS sandbox.
    """
    def __init__(self, agent_id: str, certior_url: str = "http://localhost:5000", api_key: str = None, handle_fallback: bool = True):
        self.agent_id = agent_id
        self.handle_fallback = handle_fallback
        self.client = CertiorClient(endpoint=certior_url, api_key=api_key)
        CertiorSandbox.initialize(secret_key=api_key)

    def wrap_executor(self, executor: Any, required_capabilities: list[str]) -> Any:
        """
        Wraps a LangChain Action Executor. When `invoke` or `run` is called,
        it evaluates mathematics first and bounds the Python process context.
        """
        original_invoke = getattr(executor, "invoke", None)
        if not original_invoke:
            raise AttributeError("Provided executor does not have an 'invoke' method. Ensure it is a LangChain Runnable/AgentExecutor")
            
        @functools.wraps(original_invoke)
        def secured_invoke(input_data: Any, *args, **kwargs) -> Any:
            request_hash = str(hash(str(input_data)))
            
            try:
                # Phase 9.1: Agent-Facing Proof API Loop
                signed_token = self.client.request_delegation(
                    agent_id=self.agent_id,
                    request_hash=request_hash,
                    required_capabilities=required_capabilities
                )
                
                # Phase 9.4: Sandbox hook wrapper
                with CertiorSandbox.assume_capabilities(signed_token):
                    return original_invoke(input_data, *args, **kwargs)
            except CertiorSecurityError as e:
                # Phase 9.6: Failure Recovery and Fallback Handling 
                if self.handle_fallback:
                    return format_safe_llm_rejection(e)
                raise e

        # Patch the executor
        executor.invoke = secured_invoke
        return executor
