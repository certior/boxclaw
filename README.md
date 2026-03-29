<p align="center">
  <img src="https://raw.githubusercontent.com/certior/boxclaw/main/assets/logo.svg" width="280" alt="Certior Logo">
</p>

# BoxClaw SDK

[![PyPI version](https://badge.fury.io/py/boxclaw.svg)](https://badge.fury.io/py/boxclaw)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Zero-Trust Runtime Execution Sandboxing for AI Agents**

The `boxclaw` SDK acts as the execution-environment boundary for LLMs operating inside agent frameworks (like LangChain, OpenClaw, SmolAgents, or custom OpenAI scripts). By wrapping standard Python operations in our native OS-Hooks (`sys.addaudithook`), any AI acting through the functions decorated with our `@boxclaw_guardrail` must provide deterministic proof that its intended behavior adheres to local security invariants.

This is fundamentally different from semantic guardrails: BoxClaw catches the actual OS system calls, FFI loads (like `ctypes`), network requests, and filesystem writes exactly at the CPython Virtual Machine level.

## Installation

```bash
pip install boxclaw
```

## Usage

Agent frameworks often grant LLMs unrestricted access to local system resources (e.g., executing arbitrary Bash commands or running generated Python scripts). BoxClaw allows you to restrict the AI to authorized capabilities *only*. 

To set it up, simply wrap the function your Agent uses with the `@boxclaw_guardrail` and declare exactly what operations it is allowed to perform.

### Example: Securing a File Agent

```python
from boxclaw import boxclaw_guardrail
import subprocess
import os

# Limit the agent strictly to Network requests.
# It is completely blocked from modifying the File System or running Bash Commands.
@boxclaw_guardrail(agent_id="web-crawler-bot", required_capabilities=["network_send"])
def agent_execute(llm_generated_code: str):
    # DANGEROUS! If the LLM generates malicious code here (e.g. `import os; os.system('rm -rf /')`),
    # BoxClaw will instantly catch the deep OS call and throw a PermissionError Exception.
    exec(llm_generated_code)

try:
    # This will trigger the Sandbox Security Guard and throw an exception
    # because the agent ONLY has network_send capabilities.
    malicious_ai_action = "with open('stolen_data.txt', 'w') as f: f.write('secret')"
    agent_execute(malicious_ai_action)
except Exception as e:
    print(f"Blocked by BoxClaw: {e}")
```

## Security Capabilities

You can specify specific scopes to limit your LLMs strictly to the tasks you hired them to do:

- **`system_execute`**: Blocks arbitrary subprocess commands
- **`network_send`**: Blocks unauthorized HTTP/socket connections
- **`write_fs`**: Prevents the agent from modifying the filesystem
- **`ffi_load`**: Mathematically blocks C-Extensions / `ctypes` sandbox escapes

## Links
* **PyPI Package**: [https://pypi.org/project/boxclaw/](https://pypi.org/project/boxclaw/)
* **GitHub Repository**: [https://github.com/certior/boxclaw](https://github.com/certior/boxclaw)
