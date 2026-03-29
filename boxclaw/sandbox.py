import sys
import contextvars
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import requests
import jwt

_current_agent_token = contextvars.ContextVar('certior_capability_token', default=None)
_CERTIOR_SYSTEM_SECRET = "CERTIOR_FALLBACK_SECRET_CHANGE_ME_IN_PROD"

class CertiorSecurityError(Exception):
    pass

def _certior_audit_hook(event: str, args: tuple):
    token_str = _current_agent_token.get()
    if token_str is None:
        return
    try:
        payload = jwt.decode(token_str, _CERTIOR_SYSTEM_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError as e:
        raise CertiorSecurityError(f"[Certior Sandbox] Invalid Capability Token: {e}")
        
    permissions = payload.get("permissions", [])
    agent_id = payload.get("agent_id", "unknown")

    if event == "socket.connect":
        if "network_send" not in permissions and "admin:network_all" not in permissions:
            raise CertiorSecurityError(f"Mathematical Proof Refusal: Agent {agent_id} lacks 'network_send'.")
            
    if event in ("subprocess.Popen", "os.system", "os.execv", "os.spawnv"):
        if "system_execute" not in permissions:
            raise CertiorSecurityError(f"Mathematical Proof Refusal: Agent {agent_id} lacks 'system_execute'.")

    # [FIX C-EXTENSION / SHARED LIBRARY BYPASS LIMITATION]
    if event in ("ctypes.dlopen", "ctypes.dlsym", "_ctypes.dlopen", "_ctypes.dlsym"):
        if "ffi_load" not in permissions and "admin:ffi_all" not in permissions:
            raise CertiorSecurityError(f"Glass Box Verification Refusal: Agent {agent_id} attempted unsafe foreign function call via {event} without 'ffi_load'.")

    if event == "open" and len(args) >= 2:
        mode_str = str(args[1])
        if ('w' in mode_str or 'a' in mode_str or '+' in mode_str) and "write_fs" not in permissions:
            raise CertiorSecurityError(f"Mathematical Proof Refusal: Agent {agent_id} lacks 'write_fs'.")

class CertiorSandbox:
    _installed = False
    
    def __init__(self, api_url: str = "http://localhost:8000/api/v1/agents", api_key: str = "dev-orchestrator-key-12345"):
        self.api_url = api_url
        self.api_key = api_key

    def enable(self):
        self.__class__.initialize()

    @staticmethod
    def initialize(secret_key: str = None):
        global _CERTIOR_SYSTEM_SECRET
        if secret_key:
             _CERTIOR_SYSTEM_SECRET = secret_key
             
        if not CertiorSandbox._installed:
            try:
                sys.addaudithook(_certior_audit_hook)
                CertiorSandbox._installed = True
            except Exception:
                pass

    @staticmethod
    @contextmanager
    def assume_capabilities(signed_token: str):
        token_var = _current_agent_token.set(signed_token)
        try:
            yield
        finally:
            _current_agent_token.reset(token_var)
            
    def verify_and_issue_token(self, agent_id: str, intent: List[str]) -> str:
        from .middlewares import CertiorClient
        client = CertiorClient(endpoint=self.api_url, api_key=self.api_key)
        import hashlib
        req_hash = hashlib.sha256(f"{agent_id}-{intent}".encode()).hexdigest()[:16]
        return client.request_delegation(
            agent_id=str(agent_id),
            request_hash=req_hash,
            required_capabilities=intent
        )

def current_capabilities():
    return _current_agent_token.get()

sandbox_context = CertiorSandbox.assume_capabilities
