import functools
import requests
from typing import Callable, Any, Optional

from .sandbox import CertiorSandbox, CertiorSecurityError
from .fallback import format_safe_llm_rejection

class CertiorClient:
    """
    Communicates with the Core Certior Lean 4 Backend (running locally or in the cloud).
    """
    def __init__(self, endpoint: str = "http://localhost:8000/api/v1/agents", api_key: str = "dev-orchestrator-key-12345"):
        if not endpoint.startswith("http"):
            endpoint = f"http://{endpoint}"
        self.endpoint = endpoint
        self.api_key = api_key

    def request_delegation(self, agent_id: str, request_hash: str, required_capabilities: list[str]) -> str:
        """
        Calls the Core API to verify mathematical proofs that `agent_id`
        can execute `required_capabilities`. Returns a signed JWT valid for the OS Sandbox.
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "parent_id": "root",
            "parent_agent_id": "system_orchestrator",
            "parent_permissions": required_capabilities,
            "parent_budget": 10000,
            "child_id": request_hash,
            "child_agent_id": agent_id,
            "child_permissions": required_capabilities,
            "child_budget": 100
        }
        
        try:
            res = requests.post(f"{self.endpoint}/delegate", json=payload, headers=headers)
        except Exception as e:
            print(f"[Certior] Offline mode or connection failed: {e}")
            from .cli import generate_mock_token
            return generate_mock_token(agent_id, required_capabilities)

        if res.status_code == 200:
            return res.json().get("token_id", "")
        elif res.status_code in (400, 422, 401, 403):
             err_msg = res.json().get('detail', res.text)
             raise CertiorSecurityError(f"Certior Mathematical Verification Failed: {err_msg}")
        
        raise RuntimeError(f"Certior Backend Error {res.status_code}: {res.text}")

def nemoclaw_guardrail(
    agent_id: str,
    required_capabilities: list[str],
    certior_url: str = "http://localhost:8000/api/v1/agents",
    handle_fallback: bool = True
):
    """
    Decorator for NemoClaw/OpenClaw functions. 
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                CertiorSandbox.initialize()
                client = CertiorClient(endpoint=certior_url)
                
                exec_hash = str(hash(func.__name__))

                signed_token = client.request_delegation(
                    agent_id=str(agent_id),
                    request_hash=exec_hash,
                    required_capabilities=required_capabilities
                )
                
                with CertiorSandbox.assume_capabilities(signed_token):
                    return func(*args, **kwargs)
            except CertiorSecurityError as e:
                if handle_fallback:
                    return format_safe_llm_rejection(e)
                raise e
        return wrapper
    return decorator

def openclaw_guardrail(*args, **kwargs):
    return nemoclaw_guardrail(*args, **kwargs)
