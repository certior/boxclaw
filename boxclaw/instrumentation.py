import sqlite3
import json
import os
import requests
from datetime import datetime
from certior_core.schema import AgentTraceEvent

class CertiorLocalLogger:
    def __init__(self, db_path='.agentsafe/local_trace.sqlite'):
        self.db_path = db_path
        self._setup_db()

    def _setup_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                agent_framework TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                policy_reference TEXT,
                status TEXT NOT NULL,
                math_proof_hash TEXT
            )
        """)
        self.conn.commit()

    def log_event(self, event: AgentTraceEvent):
        payload_str = json.dumps(event.payload) if event.payload else "{}"
        self.conn.execute(
            """INSERT INTO traces 
               (trace_id, agent_framework, timestamp, action_type, payload, policy_reference, status, math_proof_hash) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.trace_id,
                event.agent_framework,
                event.timestamp.isoformat(),
                event.action_type,
                payload_str,
                event.policy_reference,
                event.status,
                event.math_proof_hash
            )
        )
        self.conn.commit()


def wrap_agent(agent_instance, framework_name="generic", api_base_url="http://localhost:8001"):
    """
    A generic monkey-patching wrapper for agent step functions.
    It intercepts the 'step' or 'run' method if it exists and asks Certior API to evaluate the plan first.
    """
    logger = CertiorLocalLogger()
    
    if hasattr(agent_instance, 'step'):
        original_step = agent_instance.step
        
        def hooked_step(*args, **kwargs):
            import uuid
            trace_id = str(uuid.uuid4())
            
            # --- PHASE 9.1: Call the Agent-Facing Proof API BEFORE executing ---
            intent_payload = {
                "framework": framework_name,
                "action_type": "step_execution",
                "payload": {"args": str(args), "kwargs": str(kwargs)}
            }
            
            try:
                resp = requests.post(f"{api_base_url}/api/v1/agents/verify-plan", json=intent_payload, timeout=5.0)
                resp.raise_for_status()
                verification = resp.json()
                
                if not verification.get("allowed", False):
                    reason = verification.get("reason", "Unknown lattice violation")
                    logger.log_event(AgentTraceEvent(
                        trace_id=trace_id,
                        agent_framework=framework_name,
                        action_type="step_blocked",
                        payload={"args": str(args), "reason": reason},
                        status="BLOCKED"
                    ))
                    raise ValueError(f"Certior Mathematical Sandbox Blocked Action: {reason}")
            except requests.RequestException as e:
                # Fail closed on API unavailability to ensure strict sandboxing
                raise RuntimeError(f"Certior Verification API unreachable. Halting agent for safety: {e}")
            
            # --- Action is safe according to the proof, proceed ---

            # Log intention
            logger.log_event(AgentTraceEvent(
                trace_id=trace_id,
                agent_framework=framework_name,
                action_type="step_started",
                payload={"args": str(args), "kwargs": str(kwargs)},
                status="ALLOWED"
            ))
            
            try:
                result = original_step(*args, **kwargs)
                
                # Log completion
                logger.log_event(AgentTraceEvent(
                    trace_id=trace_id,
                    agent_framework=framework_name,
                    action_type="step_completed",
                    payload={"result": str(result)},
                    status="ALLOWED"
                ))
                return result
            except Exception as e:
                # Log error / block
                logger.log_event(AgentTraceEvent(
                    trace_id=trace_id,
                    agent_framework=framework_name,
                    action_type="step_failed",
                    payload={"error": str(e)},
                    status="ERROR"
                ))
                raise e
                
        agent_instance.step = hooked_step
        
    return agent_instance
