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
    """JSON formatter that dynamically extracts all extra fields."""

    # Standard LogRecord attributes to exclude (these are Python logging internals)
    STANDARD_ATTRS = {
        'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
        'levelno', 'lineno', 'module', 'msecs', 'message', 'pathname', 'process',
        'processName', 'relativeCreated', 'thread', 'threadName', 'exc_info',
        'exc_text', 'stack_info', 'asctime'
    }

    def format(self, record):
        # Base fields
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }

        # Dynamically extract all extra fields (exclude standard LogRecord attrs)
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_ATTRS and not key.startswith('_'):
                # Serialize complex objects (like usage dicts) properly
                try:
                    json.dumps(value)  # Test if JSON-serializable
                    log_record[key] = value
                except (TypeError, ValueError):
                    # Non-serializable (e.g., Exception objects) - convert to string
                    log_record[key] = str(value)

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
