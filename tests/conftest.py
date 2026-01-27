"""Pytest configuration for AgentLeeOps tests."""
import sys
from pathlib import Path

# Add project root to path so 'lib' module can be imported
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
