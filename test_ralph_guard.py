import subprocess
from pathlib import Path
from agents.ralph import verify_no_test_changes

def test_ralph_git_guard():
    dirname = "ralph-guard-test"
    workspace = Path.home() / "projects" / dirname
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Init git if needed
    if not (workspace / ".git").exists():
        subprocess.run(["git", "init"], cwd=workspace)
        
    test_dir = workspace / "tests"
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test_fake.py"
    test_file.write_text("assert True")
    
    src_dir = workspace / "src"
    src_dir.mkdir(exist_ok=True)
    src_file = src_dir / "app.py"
    src_file.write_text("x = 1")
    
    print(f"--- Testing Ralph Git Guard in {workspace} ---")
    
    # 1. Stage only SRC
    print("1. Staging only src/app.py...")
    subprocess.run(["git", "add", "src/app.py"], cwd=workspace)
    ok, offending = verify_no_test_changes(workspace)
    if ok:
        print("✅ SUCCESS: Guard allowed src staging.")
    else:
        print(f"❌ FAIL: Guard blocked src staging unexpectedly: {offending}")
        return False
        
    # 2. Stage TEST
    print("2. Staging tests/test_fake.py...")
    subprocess.run(["git", "add", "tests/test_fake.py"], cwd=workspace)
    ok, offending = verify_no_test_changes(workspace)
    if not ok:
        print(f"✅ SUCCESS: Guard BLOCKED test staging: {offending}")
    else:
        print("❌ FAIL: Guard ALLOWED test staging!")
        return False
        
    # Cleanup for next test runs
    subprocess.run(["git", "reset"], cwd=workspace)
    
    print("\n--- Ralph Guard Test Suite Passed ---")
    return True

if __name__ == "__main__":
    test_ralph_git_guard()
