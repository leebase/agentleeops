"""
Structured Logging for AgentLeeOps.
Outputs JSON-formatted logs for machine readability and observability.
"""

import json
import sys
import logging
from datetime import datetime, timezone

# Configure root logger
logger = logging.getLogger("AgentLeeOps")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        
        # Add extra fields if present
        if hasattr(record, "agent"):
            log_record["agent"] = record.agent
        if hasattr(record, "task_id"):
            log_record["task_id"] = record.task_id
        if hasattr(record, "project_id"):
            log_record["project_id"] = record.project_id
            
        return json.dumps(log_record)

handler.setFormatter(JsonFormatter())

def get_logger(agent_name: str = "SYSTEM"):
    return AgentLogger(agent_name)

class AgentLogger:
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.logger = logging.getLogger("AgentLeeOps")

    def info(self, msg, task_id=None, **kwargs):
        extra = {"agent": self.agent_name}
        if task_id: extra["task_id"] = task_id
        extra.update(kwargs)
        self.logger.info(msg, extra=extra)

    def error(self, msg, task_id=None, **kwargs):
        extra = {"agent": self.agent_name}
        if task_id: extra["task_id"] = task_id
        extra.update(kwargs)
        self.logger.error(msg, extra=extra)

    def warning(self, msg, task_id=None, **kwargs):
        extra = {"agent": self.agent_name}
        if task_id: extra["task_id"] = task_id
        extra.update(kwargs)
        self.logger.warning(msg, extra=extra)
