"""Tests for performance profiler."""

import json
import time
from pathlib import Path

import pytest

from lib.profiler import (
    ProfileEntry,
    Profiler,
    get_global_profiler,
    profile,
    profile_agent_execution,
    save_agent_profile,
    set_global_profiler,
)


class TestProfileEntry:
    """Test ProfileEntry dataclass."""

    def test_create_entry(self):
        """Should create profile entry."""
        entry = ProfileEntry(
            name="test_operation",
            start_time=time.time(),
        )

        assert entry.name == "test_operation"
        assert entry.start_time > 0
        assert entry.end_time is None
        assert entry.duration_ms is None

    def test_finish_entry(self):
        """Should finish entry and calculate duration."""
        start = time.time()
        entry = ProfileEntry(
            name="test_operation",
            start_time=start,
        )

        time.sleep(0.01)  # Sleep 10ms
        entry.finish()

        assert entry.end_time is not None
        assert entry.end_time > start
        assert entry.duration_ms is not None
        assert entry.duration_ms >= 10  # At least 10ms

    def test_entry_with_metadata(self):
        """Should store metadata."""
        entry = ProfileEntry(
            name="operation",
            start_time=time.time(),
            metadata={"key": "value", "count": 42},
        )

        assert entry.metadata["key"] == "value"
        assert entry.metadata["count"] == 42

    def test_entry_hierarchy(self):
        """Should support parent-child relationships."""
        parent = ProfileEntry(name="parent", start_time=time.time())
        child = ProfileEntry(
            name="child", start_time=time.time(), parent=parent
        )
        parent.children.append(child)

        assert child.parent == parent
        assert len(parent.children) == 1
        assert parent.children[0] == child

    def test_to_dict(self):
        """Should convert to dictionary."""
        entry = ProfileEntry(
            name="operation",
            start_time=1234567890.5,
            end_time=1234567891.5,
            duration_ms=1000,
            metadata={"key": "value"},
        )

        data = entry.to_dict()

        assert data["name"] == "operation"
        assert data["start_time"] == 1234567890.5
        assert data["end_time"] == 1234567891.5
        assert data["duration_ms"] == 1000
        assert data["metadata"] == {"key": "value"}

    def test_to_dict_with_children(self):
        """Should include children in dictionary."""
        parent = ProfileEntry(
            name="parent",
            start_time=time.time(),
        )
        parent.finish()

        child = ProfileEntry(
            name="child",
            start_time=time.time(),
            parent=parent,
        )
        child.finish()
        parent.children.append(child)

        data = parent.to_dict()

        assert "children" in data
        assert len(data["children"]) == 1
        assert data["children"][0]["name"] == "child"


class TestProfiler:
    """Test Profiler class."""

    def test_create_profiler(self):
        """Should create profiler."""
        profiler = Profiler()

        assert profiler.enabled is True
        assert len(profiler.entries) == 0

    def test_disabled_profiler(self):
        """Should support disabled profiler."""
        profiler = Profiler(enabled=False)

        with profiler.measure("operation"):
            time.sleep(0.01)

        # No entries should be recorded
        assert len(profiler.entries) == 0

    def test_measure_operation(self):
        """Should measure operation duration."""
        profiler = Profiler()

        with profiler.measure("test_op"):
            time.sleep(0.01)  # Sleep 10ms

        assert len(profiler.entries) == 1
        entry = profiler.entries[0]
        assert entry.name == "test_op"
        assert entry.duration_ms >= 10

    def test_measure_with_metadata(self):
        """Should attach metadata to measurements."""
        profiler = Profiler()

        with profiler.measure("operation", key="value", count=42):
            pass

        entry = profiler.entries[0]
        assert entry.metadata["key"] == "value"
        assert entry.metadata["count"] == 42

    def test_nested_measurements(self):
        """Should support nested measurements."""
        profiler = Profiler()

        with profiler.measure("outer"):
            time.sleep(0.01)
            with profiler.measure("inner"):
                time.sleep(0.01)

        # Check hierarchy
        assert len(profiler.entries) == 1
        outer = profiler.entries[0]
        assert outer.name == "outer"
        assert len(outer.children) == 1

        inner = outer.children[0]
        assert inner.name == "inner"
        assert inner.parent == outer
        assert inner.duration_ms >= 10

    def test_multiple_top_level_operations(self):
        """Should track multiple top-level operations."""
        profiler = Profiler()

        with profiler.measure("op1"):
            time.sleep(0.01)

        with profiler.measure("op2"):
            time.sleep(0.01)

        assert len(profiler.entries) == 2
        assert profiler.entries[0].name == "op1"
        assert profiler.entries[1].name == "op2"

    def test_add_metadata(self):
        """Should add metadata to current operation."""
        profiler = Profiler()

        with profiler.measure("operation"):
            profiler.add_metadata(step="step1")
            time.sleep(0.01)
            profiler.add_metadata(step="step2", result="success")

        entry = profiler.entries[0]
        assert entry.metadata["step"] == "step2"  # Updated
        assert entry.metadata["result"] == "success"

    def test_get_total_duration(self):
        """Should calculate total duration."""
        profiler = Profiler()

        with profiler.measure("op1"):
            time.sleep(0.02)

        with profiler.measure("op2"):
            time.sleep(0.02)

        total = profiler.get_total_duration_ms()
        assert total >= 40  # At least 40ms

    def test_get_statistics(self):
        """Should generate statistics."""
        profiler = Profiler()

        # Multiple operations with same name
        for _ in range(3):
            with profiler.measure("repeated_op"):
                time.sleep(0.01)

        with profiler.measure("single_op"):
            time.sleep(0.01)

        stats = profiler.get_statistics()

        assert stats["total_entries"] == 4
        assert "repeated_op" in stats["operations"]
        assert stats["operations"]["repeated_op"]["count"] == 3
        assert "single_op" in stats["operations"]
        assert stats["operations"]["single_op"]["count"] == 1

    def test_statistics_with_nested_operations(self):
        """Should count nested operations in statistics."""
        profiler = Profiler()

        with profiler.measure("outer"):
            with profiler.measure("inner"):
                pass
            with profiler.measure("inner"):
                pass

        stats = profiler.get_statistics()

        # Should count both outer and inner operations
        assert stats["total_entries"] == 3
        assert stats["operations"]["outer"]["count"] == 1
        assert stats["operations"]["inner"]["count"] == 2


class TestProfilerSerialization:
    """Test profiler serialization and deserialization."""

    def test_to_dict(self):
        """Should convert profiler to dictionary."""
        profiler = Profiler()

        with profiler.measure("operation"):
            time.sleep(0.01)

        data = profiler.to_dict()

        assert "timestamp" in data
        assert "total_duration_ms" in data
        assert "entries" in data
        assert "statistics" in data
        assert len(data["entries"]) == 1

    def test_save_and_load(self, tmp_path):
        """Should save and load profiler data."""
        profiler = Profiler()

        with profiler.measure("op1", key="value"):
            time.sleep(0.01)
            with profiler.measure("op2"):
                time.sleep(0.01)

        # Save
        filepath = tmp_path / "profile.json"
        profiler.save(filepath)

        assert filepath.exists()

        # Load
        loaded = Profiler.load(filepath)

        # Verify
        assert len(loaded.entries) == 1
        assert loaded.entries[0].name == "op1"
        assert loaded.entries[0].metadata["key"] == "value"
        assert len(loaded.entries[0].children) == 1
        assert loaded.entries[0].children[0].name == "op2"

    def test_save_creates_directory(self, tmp_path):
        """Should create directory if it doesn't exist."""
        profiler = Profiler()

        with profiler.measure("operation"):
            pass

        filepath = tmp_path / "subdir" / "profile.json"
        profiler.save(filepath)

        assert filepath.exists()


class TestGlobalProfiler:
    """Test global profiler functionality."""

    def test_get_global_profiler(self):
        """Should get global profiler instance."""
        profiler = get_global_profiler()

        assert profiler is not None
        assert isinstance(profiler, Profiler)

        # Should return same instance
        profiler2 = get_global_profiler()
        assert profiler2 is profiler

    def test_set_global_profiler(self):
        """Should set global profiler."""
        custom_profiler = Profiler()
        set_global_profiler(custom_profiler)

        retrieved = get_global_profiler()
        assert retrieved is custom_profiler

        # Clean up
        set_global_profiler(None)

    def test_profile_decorator(self):
        """Should profile function with decorator."""
        # Reset global profiler
        set_global_profiler(Profiler())

        @profile("test_function")
        def my_function():
            time.sleep(0.01)
            return 42

        result = my_function()

        assert result == 42

        profiler = get_global_profiler()
        assert len(profiler.entries) == 1
        assert profiler.entries[0].name == "test_function"
        assert profiler.entries[0].duration_ms >= 10

        # Clean up
        set_global_profiler(None)

    def test_profile_decorator_default_name(self):
        """Should use function name if no name provided."""
        set_global_profiler(Profiler())

        @profile()
        def my_custom_function():
            pass

        my_custom_function()

        profiler = get_global_profiler()
        assert profiler.entries[0].name == "my_custom_function"

        # Clean up
        set_global_profiler(None)

    def test_profile_decorator_with_metadata(self):
        """Should attach metadata to profiled function."""
        set_global_profiler(Profiler())

        @profile("operation", category="test", version=1)
        def my_function():
            pass

        my_function()

        profiler = get_global_profiler()
        entry = profiler.entries[0]
        assert entry.metadata["category"] == "test"
        assert entry.metadata["version"] == 1

        # Clean up
        set_global_profiler(None)


class TestAgentProfiling:
    """Test agent profiling utilities."""

    def test_profile_agent_execution(self):
        """Should create profiler for agent execution."""
        profiler = profile_agent_execution("TEST_AGENT", "123")

        assert profiler is not None
        assert isinstance(profiler, Profiler)
        assert profiler.enabled is True

        # Should be set as global profiler
        assert get_global_profiler() is profiler

        # Clean up
        set_global_profiler(None)

    def test_save_agent_profile(self, tmp_path):
        """Should save agent profile to workspace."""
        profiler = Profiler()

        with profiler.measure("agent_operation"):
            time.sleep(0.01)

        # Save
        filepath = save_agent_profile(profiler, tmp_path, "TEST_AGENT")

        # Verify
        assert filepath.exists()
        assert filepath.parent == tmp_path / ".agentleeops" / "profiles"
        assert "TEST_AGENT" in filepath.name
        assert filepath.suffix == ".json"

        # Load and verify
        with open(filepath) as f:
            data = json.load(f)

        assert len(data["entries"]) == 1
        assert data["entries"][0]["name"] == "agent_operation"


class TestProfilerIntegration:
    """Test profiler integration scenarios."""

    def test_complex_agent_workflow(self, tmp_path):
        """Should profile complex agent workflow."""
        profiler = Profiler()

        with profiler.measure("agent_execution", agent="TEST"):
            with profiler.measure("load_config"):
                time.sleep(0.005)

            with profiler.measure("llm_call", role="planner", model="gpt-4"):
                time.sleep(0.02)

            with profiler.measure("file_operations"):
                with profiler.measure("read_file", file="design.md"):
                    time.sleep(0.003)
                with profiler.measure("write_file", file="output.py"):
                    time.sleep(0.003)

            with profiler.measure("git_operations"):
                with profiler.measure("git_add"):
                    time.sleep(0.005)
                with profiler.measure("git_commit"):
                    time.sleep(0.01)

        # Verify structure
        assert len(profiler.entries) == 1
        agent_exec = profiler.entries[0]
        assert agent_exec.name == "agent_execution"
        assert len(agent_exec.children) == 4

        # Verify statistics
        stats = profiler.get_statistics()
        # 1 agent_exec + 4 direct children + 2 file ops + 2 git ops = 9 total
        assert stats["total_entries"] == 9
        assert "llm_call" in stats["operations"]
        assert "git_add" in stats["operations"]

        # Save and verify
        filepath = tmp_path / "profile.json"
        profiler.save(filepath)

        loaded = Profiler.load(filepath)
        assert len(loaded.entries) == 1
        assert loaded.entries[0].name == "agent_execution"

    def test_multiple_agent_runs(self):
        """Should track multiple agent runs."""
        profiler = Profiler()

        # First run
        with profiler.measure("agent_run", run=1):
            with profiler.measure("llm_call"):
                time.sleep(0.01)

        # Second run
        with profiler.measure("agent_run", run=2):
            with profiler.measure("llm_call"):
                time.sleep(0.01)

        # Verify
        assert len(profiler.entries) == 2
        stats = profiler.get_statistics()
        assert stats["operations"]["agent_run"]["count"] == 2
        assert stats["operations"]["llm_call"]["count"] == 2
