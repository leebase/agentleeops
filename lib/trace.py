"""
Trace Store.
Logs LLM interactions to a local SQLite database for cost tracking and debugging.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

TRACE_DB_PATH = Path(".agentleeops/trace.db")

def init_trace_db():
    TRACE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(TRACE_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            agent TEXT,
            model TEXT,
            prompt_len INTEGER,
            response_len INTEGER,
            prompt_preview TEXT,
            response_preview TEXT,
            full_log_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_trace(agent: str, model: str, prompt: str, response: str):
    try:
        init_trace_db() # Ensure exists
        
        # Save full content to file for deep debug
        timestamp = datetime.now(timezone.utc).isoformat()
        log_dir = TRACE_DB_PATH.parent / "logs" / agent
        log_dir.mkdir(parents=True, exist_ok=True)
        log_filename = f"{timestamp.replace(':','-')}.json"
        log_path = log_dir / log_filename
        
        log_content = {
            "timestamp": timestamp,
            "agent": agent,
            "model": model,
            "prompt": prompt,
            "response": response
        }
        log_path.write_text(json.dumps(log_content, indent=2))
        
        # Log summary to DB
        conn = sqlite3.connect(TRACE_DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO traces (timestamp, agent, model, prompt_len, response_len, prompt_preview, response_preview, full_log_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, 
            agent, 
            model, 
            len(prompt), 
            len(response), 
            prompt[:100], 
            response[:100], 
            str(log_path)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging trace: {e}")
