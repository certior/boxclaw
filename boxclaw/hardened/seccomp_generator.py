import json

def generate_docker_seccomp_from_token(agent_id: str, permissions: list[str]) -> str:
    """
    Translates mathematical Certior capabilities into a strictly 
    enforced Docker Seccomp JSON profile. 
    Prevents ANY compiled C-extensions or OS-tools from bypassing python's PEP578.
    """
    
    # Default drop-all profile template (Enterprise Grade)
    profile = {
        "defaultAction": "SCMP_ACT_ERRNO",
        "architectures": [
            "SCMP_ARCH_X86_64",
            "SCMP_ARCH_AARCH64"
        ],
        "syscalls": [
             # Minimum required for python to simply run and sleep, 
             # without networking, files, or execution.
             {
                 "names": ["read", "write", "close", "fstat", "mmap", "mprotect", "munmap", "brk", "rt_sigaction", "rt_sigprocmask", "ioctl", "getpid", "getuid", "exit_group", "futex"],
                 "action": "SCMP_ACT_ALLOW"
             }
        ]
    }
    
    # Map Certior permissions to kernel syscalls natively
    if "network_send" in permissions or "admin:network_all" in permissions:
        profile["syscalls"].append({
            "names": ["socket", "connect", "sendto", "recvfrom", "sendmsg", "recvmsg", "bind", "setsockopt"],
            "action": "SCMP_ACT_ALLOW"
        })
        
    if "system_execute" in permissions:
        profile["syscalls"].append({
            "names": ["execve", "clone", "fork", "vfork", "wait4"],
            "action": "SCMP_ACT_ALLOW"
        })
        
    if "write_fs" in permissions:
        profile["syscalls"].append({
            "names": ["open", "openat", "mkdir", "rename", "unlink"],
            "action": "SCMP_ACT_ALLOW"
        })
    else:
         # Read only basic dependencies
         profile["syscalls"].append({
            "names": ["open", "openat"],
            "action": "SCMP_ACT_ALLOW",
            "args": [
                {
                    "index": 2, 
                    "value": 0, # O_RDONLY flag
                    "op": "SCMP_CMP_EQ"
                }
            ]
        })
        
    return json.dumps(profile, indent=2)

