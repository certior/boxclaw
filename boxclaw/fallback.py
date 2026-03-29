import json

def format_safe_llm_rejection(error: Exception) -> str:
    """
    Serializes a Lean 4 mathematical proof rejection or PEP 578 runtime interception
    into a natural language string that can be safely embedded as a System Message 
    for the LLM to self-correct its plan rather than permanently crashing.
    """
    error_msg = str(error)
    
    # Heuristics to build an actionable error prompt
    if "mathematically blocked" in error_msg.lower():
        prompt = (
            "SYSTEM OBSERVATION (Certior Glass-Box Sandbox): "
            "Your intended action mathematically violates your capability bounds. "
            f"Details: {error_msg}. "
            "Please revise your plan to use different tools or drop your restricted context."
        )
    elif "api rejection" in error_msg.lower():
        prompt = (
            "SYSTEM OBSERVATION (Certior Protocol Error): "
            f"The sandboxing API rejected the request: {error_msg}. "
            "Cannot proceed."
        )
    elif "not allowed" in error_msg.lower() or "missing capability" in error_msg.lower():
        prompt = (
            "SYSTEM OBSERVATION (Certior OS Sandbox): "
            "Your executed code attempted a system call that was intercepted and blocked "
            f"by the PEP 578 enforcing layer. Details: {error_msg}. "
            "Please rewrite your code to operate strictly within your granted capability token."
        )
    else:
        prompt = (
            "SYSTEM OBSERVATION (Security Rejection): "
            f"The sandbox blocked execution due to a strict security violation: {error_msg}. "
            "Please select a secure alternative."
        )
        
    return json.dumps({"status": "blocked_by_sandbox", "feedback": prompt})
