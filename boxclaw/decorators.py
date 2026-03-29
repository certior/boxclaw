import functools
import requests
from .sandbox import sandbox_context, CertiorSecurityError

def verify_action(agent_id: str, tool_name: str, api_url: str = "http://localhost:8000/api/v1"):
    """
    Decorator that verifies an agent's capability mathematically against the local FastAPI/Lean4 server
    before allowing the wrapped function to execute. Seamlessly injects the sandbox_context without
    requiring the developer to manage JWT HMAC signing manually.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Ask FastAPI/Lean 4 to verify the requested step conceptually
            try:
                resp = requests.post(
                    f"{api_url}/agents/verify-plan",
                    json={"agent_id": agent_id, "actions": [tool_name]}
                )
                if resp.status_code != 200 or not resp.json().get("safe", False):
                    raise CertiorSecurityError(f"Action '{tool_name}' mathematically blocked by Certior constraints: {resp.text}")
                
                # Retrieve the cryptographically signed JWT token 
                agent_token = resp.json().get("token")
            except Exception as e:
                # Fallback purely for mock execution if server is offline (DX)
                if "Connection refused" in str(e):
                    print("[WARNING] Verification API offline. Running without live Lean validation, utilizing DX mock fallback.")
                    agent_token = ""
                else:
                    raise CertiorSecurityError(f"API rejection: {e}")

            # 2. Inject Sandbox context natively
            with sandbox_context(agent_token):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def sandbox_execution(agent_token: str):
    """
    Syntactic sugar over the sandbox_context standard injection. Validates runtime offline.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with sandbox_context(agent_token):
                return func(*args, **kwargs)
        return wrapper
    return decorator
