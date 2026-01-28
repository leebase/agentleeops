"""
Performance profiling for agent loops.

Provides tools to measure and analyze agent execution performance, including
LLM call times, file operations, git operations, and overall agent runtime.

Usage:
    from lib.profiler import Profiler, profile

    # Context manager
    profiler = Profiler()
    with profiler.measure("operation_name"):
        # Code to profile
        pass

    # Decorator
    @profile("my_function")
    def my_function():
        pass

    # Save profile data
    profiler.save("profile.json")

    # Analyze profile
    python tools/profile-report.py profile.json
"""

import functools
import json
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass
class ProfileEntry:
    """Single profiling entry."""

    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["ProfileEntry"] = field(default_factory=list)
    parent: "ProfileEntry | None" = None

    def finish(self) -> None:
        """Mark entry as finished and calculate duration."""
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = int((self.end_time - self.start_time) * 1000)

    def to_dict(self, include_children: bool = True) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

        if include_children and self.children:
            data["children"] = [c.to_dict() for c in self.children]

        return data


class Profiler:
    """Performance profiler for measuring agent execution."""

    def __init__(self, enabled: bool = True):
        """Initialize profiler.

        Args:
            enabled: Whether profiling is enabled
        """
        self.enabled = enabled
        self.entries: list[ProfileEntry] = []
        self._stack: list[ProfileEntry] = []
        self._start_time: float | None = None

    @contextmanager
    def measure(self, name: str, **metadata):
        """Context manager to measure execution time.

        Args:
            name: Name of the operation being measured
            **metadata: Additional metadata to attach to this entry

        Yields:
            ProfileEntry for this measurement
        """
        if not self.enabled:
            yield None
            return

        # Create entry
        entry = ProfileEntry(
            name=name,
            start_time=time.time(),
            metadata=metadata,
        )

        # Add to stack and hierarchy
        if self._stack:
            parent = self._stack[-1]
            entry.parent = parent
            parent.children.append(entry)
        else:
            # Top-level entry
            self.entries.append(entry)

        self._stack.append(entry)

        try:
            yield entry
        finally:
            # Finish timing
            entry.finish()
            self._stack.pop()

    def add_metadata(self, **metadata) -> None:
        """Add metadata to current operation.

        Args:
            **metadata: Metadata to add
        """
        if self._stack and self.enabled:
            self._stack[-1].metadata.update(metadata)

    def get_total_duration_ms(self) -> int:
        """Get total duration of all top-level entries.

        Returns:
            Total duration in milliseconds
        """
        return sum(e.duration_ms or 0 for e in self.entries)

    def get_statistics(self) -> dict[str, Any]:
        """Get profiling statistics.

        Returns:
            Dict with statistics about profiled operations
        """
        if not self.entries:
            return {
                "total_entries": 0,
                "total_duration_ms": 0,
                "operations": {},
            }

        # Flatten all entries
        all_entries = []

        def collect_entries(entries):
            for entry in entries:
                all_entries.append(entry)
                if entry.children:
                    collect_entries(entry.children)

        collect_entries(self.entries)

        # Group by operation name
        operations = {}
        for entry in all_entries:
            if entry.name not in operations:
                operations[entry.name] = {
                    "count": 0,
                    "total_ms": 0,
                    "min_ms": float("inf"),
                    "max_ms": 0,
                    "avg_ms": 0,
                }

            stats = operations[entry.name]
            stats["count"] += 1
            stats["total_ms"] += entry.duration_ms or 0
            stats["min_ms"] = min(stats["min_ms"], entry.duration_ms or 0)
            stats["max_ms"] = max(stats["max_ms"], entry.duration_ms or 0)

        # Calculate averages
        for stats in operations.values():
            if stats["count"] > 0:
                stats["avg_ms"] = stats["total_ms"] // stats["count"]

        return {
            "total_entries": len(all_entries),
            "total_duration_ms": self.get_total_duration_ms(),
            "operations": operations,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert profiler data to dictionary.

        Returns:
            Dict representation of profiler data
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_duration_ms": self.get_total_duration_ms(),
            "entries": [e.to_dict() for e in self.entries],
            "statistics": self.get_statistics(),
        }

    def save(self, filepath: str | Path) -> None:
        """Save profiling data to file.

        Args:
            filepath: Path to save profiling data
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str | Path) -> "Profiler":
        """Load profiling data from file.

        Args:
            filepath: Path to profiling data file

        Returns:
            Profiler instance with loaded data
        """
        with open(filepath) as f:
            data = json.load(f)

        profiler = cls(enabled=True)

        # Reconstruct entries
        def reconstruct_entry(entry_data, parent=None):
            entry = ProfileEntry(
                name=entry_data["name"],
                start_time=entry_data["start_time"],
                end_time=entry_data.get("end_time"),
                duration_ms=entry_data.get("duration_ms"),
                metadata=entry_data.get("metadata", {}),
                parent=parent,
            )

            # Reconstruct children
            for child_data in entry_data.get("children", []):
                child = reconstruct_entry(child_data, parent=entry)
                entry.children.append(child)

            return entry

        for entry_data in data.get("entries", []):
            entry = reconstruct_entry(entry_data)
            profiler.entries.append(entry)

        return profiler


# Global profiler instance for decorator usage
_global_profiler: Profiler | None = None


def get_global_profiler() -> Profiler:
    """Get or create global profiler instance.

    Returns:
        Global Profiler instance
    """
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = Profiler()
    return _global_profiler


def set_global_profiler(profiler: Profiler | None) -> None:
    """Set global profiler instance.

    Args:
        profiler: Profiler instance or None to disable
    """
    global _global_profiler
    _global_profiler = profiler


def profile(name: str | None = None, **metadata):
    """Decorator to profile function execution.

    Args:
        name: Optional custom name for the operation (defaults to function name)
        **metadata: Additional metadata to attach

    Returns:
        Decorated function

    Example:
        @profile("expensive_operation")
        def my_function():
            # ...
            pass
    """

    def decorator(func: Callable) -> Callable:
        operation_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = get_global_profiler()

            with profiler.measure(operation_name, **metadata):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def profile_agent_execution(agent_name: str, task_id: str) -> Profiler:
    """Create profiler for agent execution.

    Args:
        agent_name: Name of the agent
        task_id: Kanboard task ID

    Returns:
        Profiler instance configured for this agent execution
    """
    profiler = Profiler(enabled=True)

    # Set as global profiler for decorator usage
    set_global_profiler(profiler)

    return profiler


def save_agent_profile(profiler: Profiler, workspace: Path, agent_name: str) -> Path:
    """Save agent profiling data.

    Args:
        profiler: Profiler instance
        workspace: Workspace path
        agent_name: Agent name

    Returns:
        Path to saved profile file
    """
    # Create profiles directory
    profiles_dir = workspace / ".agentleeops" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{agent_name}_{timestamp}.json"
    filepath = profiles_dir / filename

    # Save profile
    profiler.save(filepath)

    return filepath
