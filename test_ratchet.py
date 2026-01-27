import sys
from pathlib import Path
from lib.workspace import safe_write_file, get_workspace_path
from lib.ratchet import lock_artifact, unlock_artifact, check_write_permission

def test_ratchet_logic():
    dirname = "ratchet-test-project"
    workspace = get_workspace_path(dirname)
    workspace.mkdir(parents=True, exist_ok=True)
    
    filename = "LOCKED_FILE.md"
    content_v1 = "Initial Content"
    content_v2 = "Illegal Update"
    
    print(f"--- Testing Ratchet in {workspace} ---")
    
    # 1. Initial Write
    print("1. Writing initial file...")
    safe_write_file(workspace, filename, content_v1)
    
    # 2. Lock it
    print("2. Locking file...")
    lock_artifact(workspace, filename)
    
    # 3. Try to overwrite (Should fail)
    print("3. Attempting to overwrite locked file...")
    try:
        safe_write_file(workspace, filename, content_v2)
        print("❌ FAIL: Overwrote locked file!")
        return False
    except PermissionError as e:
        print(f"✅ SUCCESS: Caught expected error: {e}")
        
    # 4. Unlock it
    print("4. Unlocking file...")
    unlock_artifact(workspace, filename, reason="Manual Test Override")
    
    # 5. Try to overwrite (Should succeed)
    print("5. Attempting to overwrite unlocked file...")
    try:
        safe_write_file(workspace, filename, content_v2)
        print("✅ SUCCESS: File updated after unlock.")
    except PermissionError as e:
        print(f"❌ FAIL: Could not update unlocked file: {e}")
        return False
        
    print("\n--- Ratchet Test Suite Passed ---")
    return True

if __name__ == "__main__":
    if not test_ratchet_logic():
        sys.exit(1)
