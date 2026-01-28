"""
Integration tests for KanboardWorkItemProvider.

These tests connect to a real Kanboard instance.
Requires: Kanboard running on port 188 with valid credentials in .env
"""

import os
import pytest
from dotenv import load_dotenv

# Load environment before imports
load_dotenv()

from lib.workitem.types import (
    WorkItem,
    WorkItemIdentity,
    WorkItemQuery,
    WorkItemState,
)
from lib.workitem.providers.kanboard import KanboardWorkItemProvider
from lib.workitem.config import load_provider_config


# Skip all tests if no Kanboard token configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("KANBOARD_TOKEN"),
    reason="KANBOARD_TOKEN not set - skipping integration tests"
)


@pytest.fixture
def provider():
    """Create provider instance with config from environment."""
    config = load_provider_config()
    provider_config = config.get("providers", {}).get("kanboard", {})
    return KanboardWorkItemProvider(provider_config)


@pytest.fixture
def kanboard_url():
    """Get Kanboard URL from environment."""
    return os.environ.get("KANBOARD_URL", "http://localhost:188/jsonrpc.php")


class TestKanboardProviderConnection:
    """Test basic connectivity to Kanboard."""

    def test_provider_name(self, provider):
        """Provider should identify as 'kanboard'."""
        assert provider.name == "kanboard"

    def test_client_connects(self, provider):
        """Should connect and get API version."""
        # Just verify we can make a call
        try:
            version = provider.client.get_version()
            assert version is not None
            print(f"Connected to Kanboard version: {version}")
        except Exception as e:
            pytest.fail(f"Failed to connect to Kanboard: {e}")


class TestKanboardProviderQuery:
    """Test querying work items."""

    def test_query_all_tasks(self, provider):
        """Should query all tasks in default project."""
        query = WorkItemQuery()
        items = provider.query_work_items(query)
        
        # Should return a list (may be empty)
        assert isinstance(items, list)
        print(f"Found {len(items)} work items")
        
        # If items exist, verify they are WorkItems
        for item in items[:3]:  # Check first 3
            assert isinstance(item, WorkItem)
            assert item.identity.provider == "kanboard"
            assert item.identity.external_id
            assert item.title

    def test_query_with_project_id(self, provider):
        """Should query tasks in specific project."""
        query = WorkItemQuery(project_id="1")
        items = provider.query_work_items(query)
        assert isinstance(items, list)

    def test_query_with_limit(self, provider):
        """Should respect limit parameter."""
        query = WorkItemQuery(limit=2)
        items = provider.query_work_items(query)
        assert len(items) <= 2


class TestKanboardProviderGetWorkItem:
    """Test fetching individual work items."""

    def test_get_existing_task(self, provider):
        """Should fetch a task that exists."""
        # First, query to find a task
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        # Fetch the same task by ID
        identity = items[0].identity
        item = provider.get_work_item(identity)
        
        assert item is not None
        assert item.identity.external_id == identity.external_id
        assert item.title == items[0].title

    def test_get_nonexistent_task(self, provider):
        """Should return None for non-existent task."""
        identity = WorkItemIdentity(
            provider="kanboard",
            external_id="999999"  # Unlikely to exist
        )
        item = provider.get_work_item(identity)
        assert item is None


class TestKanboardProviderTags:
    """Test tag operations."""

    def test_get_tags_for_task(self, provider):
        """Should get tags for a task."""
        # Find a task
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        tags = provider.get_tags(items[0].identity)
        assert isinstance(tags, list)
        print(f"Task tags: {tags}")


class TestKanboardProviderStateMapping:
    """Test column-to-state mapping."""

    def test_state_is_valid_enum(self, provider):
        """Work items should have valid WorkItemState."""
        query = WorkItemQuery(limit=5)
        items = provider.query_work_items(query)
        
        for item in items:
            assert isinstance(item.state, WorkItemState)
            print(f"Task '{item.title}' -> state: {item.state.value}")


class TestKanboardProviderMetadata:
    """Test metadata and field extraction."""

    def test_work_item_has_metadata(self, provider):
        """Work items should have metadata dict."""
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        item = items[0]
        assert isinstance(item.metadata, dict)
        assert "project_id" in item.metadata
        assert "column_id" in item.metadata

    def test_work_item_has_timestamps(self, provider):
        """Work items should have created_at timestamp."""
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        item = items[0]
        # created_at should be set for any task
        assert item.created_at is not None


class TestKanboardProviderWriteOperations:
    """Test write operations (add/remove tag, comment, metadata)."""

    def test_add_and_remove_tag(self, provider):
        """Should add and remove a tag from a task."""
        # Find a task
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        identity = items[0].identity
        test_tag = "test-integration-tag"
        
        # Add the tag
        result = provider.add_tag(identity, test_tag)
        assert result is True
        
        # Verify tag was added
        tags = provider.get_tags(identity)
        assert test_tag in tags
        
        # Remove the tag
        result = provider.remove_tag(identity, test_tag)
        assert result is True
        
        # Verify tag was removed
        tags = provider.get_tags(identity)
        assert test_tag not in tags

    def test_add_tag_idempotent(self, provider):
        """Adding same tag twice should succeed."""
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        identity = items[0].identity
        test_tag = "idempotent-test"
        
        # Add twice
        provider.add_tag(identity, test_tag)
        result = provider.add_tag(identity, test_tag)
        assert result is True
        
        # Cleanup
        provider.remove_tag(identity, test_tag)

    def test_remove_nonexistent_tag(self, provider):
        """Removing non-existent tag should return True (idempotent)."""
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        result = provider.remove_tag(items[0].identity, "nonexistent-tag-xyz")
        assert result is True

    def test_post_comment(self, provider):
        """Should post a comment to a task."""
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        identity = items[0].identity
        comment = "Test comment from integration test"
        
        result = provider.post_comment(identity, comment)
        assert result is True

    def test_set_metadata(self, provider):
        """Should attempt to set metadata on a task (requires MetaMagik plugin)."""
        query = WorkItemQuery(limit=1)
        items = provider.query_work_items(query)
        
        if not items:
            pytest.skip("No tasks found in Kanboard")
        
        identity = items[0].identity
        
        # Set a test metadata field - may fail if MetaMagik not installed
        result = provider.set_metadata(identity, "test_field", "test_value")
        # Result depends on MetaMagik plugin availability
        assert isinstance(result, bool)
        print(f"set_metadata result: {result} (False if MetaMagik not installed)")


class TestKanboardProviderStateTransition:
    """Test state transition operations."""

    def test_state_to_column_id_lookup(self, provider):
        """Should find column ID for known states."""
        # Trigger cache population
        query = WorkItemQuery(limit=1)
        provider.query_work_items(query)
        
        # Try to look up column ID for Inbox state
        col_id = provider._state_to_column_id(WorkItemState.INBOX, 1)
        # Should find a column (exact ID depends on board setup)
        print(f"Inbox column ID: {col_id}")

