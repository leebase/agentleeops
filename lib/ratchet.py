"""
Ratchet Governance System.
Manages file locking and integrity hashing to enforce the "Ratchet Effect".
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional

RATCHET_FILE = ".agentleeops/ratchet.json"

def _get_ratchet_path(workspace: Path) -> Path:
    return workspace / RATCHET_FILE

def _load_ratchet(workspace: Path) -> Dict:
    path = _get_ratchet_path(workspace)
    if not path.exists():
        return {"version": "1.0", "artifacts": {}}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"version": "1.0", "artifacts": {}}

def _save_ratchet(workspace: Path, data: Dict):
    path = _get_ratchet_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))

def calculate_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    if not file_path.exists():
        return ""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def lock_artifact(workspace: Path, relative_path: str) -> bool:
    """
    Lock an artifact in the ratchet manifest.
    Calculates current hash and sets status to LOCKED.
    """
    full_path = workspace / relative_path
    if not full_path.exists():
        return False # Cannot lock missing file

    data = _load_ratchet(workspace)
    file_hash = calculate_hash(full_path)
    
    data["artifacts"][relative_path] = {
        "status": "LOCKED",
        "hash": file_hash,
        "locked_at": str(full_path.stat().st_mtime) # Simple timestamp
    }
    
    _save_ratchet(workspace, data)
    print(f"  🔒 Ratchet: Locked {relative_path}")
    return True

def unlock_artifact(workspace: Path, relative_path: str, reason: str) -> bool:
    """Unlock an artifact (requires explicit intent)."""
    data = _load_ratchet(workspace)
    if relative_path in data["artifacts"]:
        data["artifacts"][relative_path]["status"] = "UNLOCKED"
        data["artifacts"][relative_path]["unlock_reason"] = reason
        _save_ratchet(workspace, data)
        print(f"  🔓 Ratchet: Unlocked {relative_path}")
        return True
    return False

def check_write_permission(workspace: Path, relative_path: str) -> bool:
    """
    Check if a file can be written to.
    Returns True if allowed, False if Locked.
    """
    data = _load_ratchet(workspace)
    artifact = data["artifacts"].get(relative_path)
    
    if not artifact:
        return True # Not tracked = Writable
    
    if artifact["status"] == "LOCKED":
        return False
    
    return True

def verify_integrity(workspace: Path, relative_path: str) -> bool:
    """
    Verify if a file matches its locked hash.
    Useful for Ralph to ensure he hasn't accidentally touched tests.
    """
    data = _load_ratchet(workspace)
    artifact = data["artifacts"].get(relative_path)
    
    if not artifact:
        return True # Not tracked
        
    current_hash = calculate_hash(workspace / relative_path)
    return current_hash == artifact["hash"]
