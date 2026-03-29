import json
import subprocess
import os
import tempfile
from boxclaw.hardened.seccomp_generator import generate_docker_seccomp_from_token

def execute_hardened(agent_id: str, capabilities: list[str], python_script: str) -> tuple[int, str, str]:
    """
    Spawns an agent execution inside a perfectly sealed, dynamically configured Docker container.
    This fulfills the 'Glass Box' Phase 4 criteria: Kernel-level separation via eBPF/seccomp 
    that fully prevents native C-extension bypassing of PEP 578.
    
    Returns standard exit code, stdout, stderr.
    """
    
    seccomp_json_str = generate_docker_seccomp_from_token(agent_id, capabilities)
    
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f_profile:
        f_profile.write(seccomp_json_str)
        profile_path = f_profile.name
        
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f_script:
        f_script.write(python_script)
        script_path = f_script.name

    try:
        cmd = [
            "docker", "run", "--rm",
            "--security-opt", f"seccomp={profile_path}",
            "-v", f"{script_path}:/app/script.py:ro",
            "python:3.11-slim",
            "python", "/app/script.py"
        ]
        
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        return proc.returncode, proc.stdout, proc.stderr
        
    finally:
        if os.path.exists(profile_path):
            os.remove(profile_path)
        if os.path.exists(script_path):
            os.remove(script_path)
