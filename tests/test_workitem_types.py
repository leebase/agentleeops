"""Tests for WorkItem types and data structures."""

from datetime import datetime

import pytest

from lib.workitem.types import (
    WorkItem,
    WorkItemIdentity,
    WorkItemQuery,
    WorkItemState,
)


class TestWorkItemState:
    """Tests for WorkItemState enum."""

    def test_all_pipeline_stages_defined(self):
        """Should have all 10 pipeline stages plus UNKNOWN."""
        expected = {
            "inbox",
            "design_draft",
            "design_approved",
            "planning_draft",
            "plan_approved",
            "tests_draft",
            "tests_approved",
            "implementation",
            "final_review",
            "done",
            "unknown",
        }
        actual = {s.value for s in WorkItemState}
        assert actual == expected

    def test_state_from_value(self):
        """Should create state from string value."""
        assert WorkItemState("inbox") == WorkItemState.INBOX
        assert WorkItemState("design_approved") == WorkItemState.DESIGN_APPROVED

    def test_invalid_state_raises(self):
        """Should raise ValueError for invalid state."""
        with pytest.raises(ValueError):
            WorkItemState("invalid_state")


class TestWorkItemIdentity:
    """Tests for WorkItemIdentity dataclass."""

    def test_creates_with_required_fields(self):
        """Should create with provider and external_id."""
        identity = WorkItemIdentity(provider="kanboard", external_id="123")
        assert identity.provider == "kanboard"
        assert identity.external_id == "123"
        assert identity.url is None

    def test_creates_with_url(self):
        """Should accept optional url."""
        identity = WorkItemIdentity(
            provider="jira",
            external_id="PROJ-456",
            url="https://jira.example.com/browse/PROJ-456",
        )
        assert identity.url == "https://jira.example.com/browse/PROJ-456"

    def test_is_frozen(self):
        """Should be immutable."""
        identity = WorkItemIdentity(provider="kanboard", external_id="123")
        with pytest.raises(AttributeError):
            identity.provider = "jira"  # type: ignore

    def test_is_hashable(self):
        """Should be usable as dict key."""
        identity = WorkItemIdentity(provider="kanboard", external_id="123")
        d = {identity: "test"}
        assert d[identity] == "test"

    def test_equality(self):
        """Equal identities should be equal."""
        id1 = WorkItemIdentity(provider="kanboard", external_id="123")
        id2 = WorkItemIdentity(provider="kanboard", external_id="123")
        assert id1 == id2

    def test_inequality(self):
        """Different identities should not be equal."""
        id1 = WorkItemIdentity(provider="kanboard", external_id="123")
        id2 = WorkItemIdentity(provider="kanboard", external_id="456")
        assert id1 != id2

    def test_str_representation(self):
        """Should have readable string representation."""
        identity = WorkItemIdentity(provider="kanboard", external_id="123")
        assert str(identity) == "kanboard:123"

    def test_set_membership(self):
        """Should be usable in sets."""
        id1 = WorkItemIdentity(provider="kanboard", external_id="123")
        id2 = WorkItemIdentity(provider="kanboard", external_id="123")
        id3 = WorkItemIdentity(provider="kanboard", external_id="456")
        s = {id1, id2, id3}
        assert len(s) == 2  # id1 and id2 are equal


class TestWorkItem:
    """Tests for WorkItem dataclass."""

    def test_creates_with_identity_and_title(self):
        """Should create with minimal required fields."""
        identity = WorkItemIdentity(provider="kanboard", external_id="1")
        item = WorkItem(identity=identity, title="Test Task")
        assert item.identity == identity
        assert item.title == "Test Task"
        assert item.description == ""
        assert item.state == WorkItemState.UNKNOWN

    def test_creates_with_all_fields(self):
        """Should accept all optional fields."""
        identity = WorkItemIdentity(provider="kanboard", external_id="1")
        now = datetime.now()
        item = WorkItem(
            identity=identity,
            title="Full Task",
            description="A complete task",
            state=WorkItemState.DESIGN_DRAFT,
            dirname="my-project",
            context_mode="NEW",
            acceptance_criteria="- Must work\n- Must be fast",
            complexity="M",
            agent_status="running",
            current_phase="design",
            tags=["design-started"],
            created_at=now,
            updated_at=now,
            metadata={"custom_field": "value"},
        )
        assert item.dirname == "my-project"
        assert item.context_mode == "NEW"
        assert item.complexity == "M"
        assert item.tags == ["design-started"]
        assert item.metadata["custom_field"] == "value"

    def test_has_tag_returns_true(self):
        """Should detect present tag."""
        identity = WorkItemIdentity(provider="kanboard", external_id="1")
        item = WorkItem(identity=identity, title="Test", tags=["foo", "bar"])
        assert item.has_tag("foo")
        assert item.has_tag("bar")

    def test_has_tag_returns_false(self):
        """Should return False for absent tag."""
        identity = WorkItemIdentity(provider="kanboard", external_id="1")
        item = WorkItem(identity=identity, title="Test", tags=["foo"])
        assert not item.has_tag("baz")

    def test_has_tag_empty_list(self):
        """Should return False for empty tags."""
        identity = WorkItemIdentity(provider="kanboard", external_id="1")
        item = WorkItem(identity=identity, title="Test")
        assert not item.has_tag("anything")


class TestWorkItemSerialization:
    """Tests for WorkItem to_dict/from_dict."""

    def test_to_dict_minimal(self):
        """Should serialize minimal item."""
        identity = WorkItemIdentity(provider="kanboard", external_id="1")
        item = WorkItem(identity=identity, title="Test")
        d = item.to_dict()
        assert d["identity"]["provider"] == "kanboard"
        assert d["identity"]["external_id"] == "1"
        assert d["title"] == "Test"
        assert d["state"] == "unknown"

    def test_to_dict_with_timestamps(self):
        """Should serialize timestamps as ISO format."""
        identity = WorkItemIdentity(provider="kanboard", external_id="1")
        now = datetime(2024, 1, 15, 10, 30, 0)
        item = WorkItem(identity=identity, title="Test", created_at=now)
        d = item.to_dict()
        assert d["created_at"] == "2024-01-15T10:30:00"

    def test_from_dict_minimal(self):
        """Should deserialize minimal dict."""
        d = {
            "identity": {"provider": "kanboard", "external_id": "1"},
            "title": "Test",
        }
        item = WorkItem.from_dict(d)
        assert item.identity.provider == "kanboard"
        assert item.identity.external_id == "1"
        assert item.title == "Test"
        assert item.state == WorkItemState.UNKNOWN

    def test_from_dict_with_state(self):
        """Should parse state correctly."""
        d = {
            "identity": {"provider": "kanboard", "external_id": "1"},
            "title": "Test",
            "state": "design_approved",
        }
        item = WorkItem.from_dict(d)
        assert item.state == WorkItemState.DESIGN_APPROVED

    def test_from_dict_invalid_state(self):
        """Should default to UNKNOWN for invalid state."""
        d = {
            "identity": {"provider": "kanboard", "external_id": "1"},
            "title": "Test",
            "state": "totally_invalid",
        }
        item = WorkItem.from_dict(d)
        assert item.state == WorkItemState.UNKNOWN

    def test_from_dict_with_timestamps(self):
        """Should parse ISO timestamps."""
        d = {
            "identity": {"provider": "kanboard", "external_id": "1"},
            "title": "Test",
            "created_at": "2024-01-15T10:30:00",
        }
        item = WorkItem.from_dict(d)
        assert item.created_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_roundtrip(self):
        """Should survive serialize/deserialize roundtrip."""
        identity = WorkItemIdentity(provider="jira", external_id="PROJ-123")
        now = datetime(2024, 6, 1, 12, 0, 0)
        original = WorkItem(
            identity=identity,
            title="Roundtrip Test",
            description="Full description",
            state=WorkItemState.IMPLEMENTATION,
            dirname="test-project",
            context_mode="FEATURE",
            tags=["started", "important"],
            created_at=now,
            metadata={"sprint": "42"},
        )
        
        d = original.to_dict()
        restored = WorkItem.from_dict(d)
        
        assert restored.identity == original.identity
        assert restored.title == original.title
        assert restored.state == original.state
        assert restored.dirname == original.dirname
        assert restored.tags == original.tags
        assert restored.created_at == original.created_at
        assert restored.metadata == original.metadata


class TestWorkItemQuery:
    """Tests for WorkItemQuery dataclass."""

    def test_creates_with_defaults(self):
        """Should create with sensible defaults."""
        query = WorkItemQuery()
        assert query.project_id is None
        assert query.states is None
        assert query.tags is None
        assert query.assignee is None
        assert query.limit == 100

    def test_creates_with_filters(self):
        """Should accept filter parameters."""
        query = WorkItemQuery(
            project_id="proj-1",
            states=[WorkItemState.INBOX, WorkItemState.DESIGN_DRAFT],
            tags=["urgent"],
            limit=50,
        )
        assert query.project_id == "proj-1"
        assert len(query.states) == 2
        assert query.tags == ["urgent"]
        assert query.limit == 50
