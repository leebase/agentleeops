# AgentLeeOps Experimental Worktree

This is an **isolated experimental development environment** for AgentLeeOps.

## Setup Details

- **Location**: `~/projects/agentleeops-next`
- **Branch**: `feat/kanban-refactor`
- **Git**: Created using `git worktree` from `~/projects/agentleeops`
- **Python**: Separate virtual environment at `./venv` (Python 3.12)
- **Dependencies**: Installed from `requirements.txt`

## Isolation from Stable Version

### Runtime State
- **State Directory**: `.agentleeops/` (local to THIS worktree)
- **Traces/Logs**: Stored in `.agentleeops/logs/` and `.agentleeops/trace.db`
- **Ratchet**: Uses `.agentleeops/ratchet.json`
- **Separation**: Completely independent from `~/projects/agentleeops/.agentleeops/`

### Configuration
- **Environment**: Uses local `.env` file (copied from `.env.example`)
- **Kanboard**: Same URL/credentials as stable version (shared state)
- **LLM Keys**: Configure separately in `.env` if needed

## Running the Experimental Version

```bash
# Activate virtual environment
source ~/projects/agentleeops-next/venv/bin/activate

# Configure .env (add API keys, etc.)
nano ~/projects/agentleeops-next/.env

# Run orchestrator (when ready)
python orchestrator.py
```

## Important Notes

1. **Do NOT modify Kanboard** - both versions use the same board
2. **State files are isolated** - logs/traces won't collide
3. **Git commits affect both worktrees** - they share the same repository
4. **Tests**: Located in `tests/` - follow Ralph's Rule (do not modify)

## Switching Between Versions

### Use Stable Version
```bash
cd ~/projects/agentleeops
source venv/bin/activate
python orchestrator.py
```

### Use Experimental Version
```bash
cd ~/projects/agentleeops-next
source venv/bin/activate
python orchestrator.py
```

## Cleanup (Future)

When done with experiments:
```bash
# From the main repo
cd ~/projects/agentleeops
git worktree remove ~/projects/agentleeops-next
```
