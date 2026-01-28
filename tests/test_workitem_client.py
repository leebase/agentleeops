"""
Unit tests for WorkItemClient and capabilities.

Uses mock provider to test delegation and capability detection.
"""

import pytest
from unittest.mock import Mock, MagicMock

from lib.workitem.types import (
    WorkItem,
    WorkItemIdentity,
    WorkItemQuery,
    WorkItemState,
)
from lib.workitem.client import WorkItemClient
from lib.workitem.capabilities import (
    Capability,
    detect_capabilities,
    has_capability,
    CAPABILITY_METHODS,
)


@pytest.fixture
def mock_provider():
    """Create a mock provider with all methods."""
    provider = Mock()
    provider.name = "mock"
    
    # Setup return values
    provider.get_work_item.return_value = WorkItem(
        identity=WorkItemIdentity(provider="mock", external_id="1"),
        title="Test Item",
    )
    provider.query_work_items.return_value = []
    provider.get_tags.return_value = ["tag1", "tag2"]
    provider.update_state.return_value = True
    provider.post_comment.return_value = True
    provider.set_metadata.return_value = True
    provider.add_tag.return_value = True
    provider.remove_tag.return_value = True
    
    return provider


@pytest.fixture
def client(mock_provider):
    """Create client with mock provider."""
    return WorkItemClient(mock_provider)


class TestWorkItemClientInit:
    """Test client initialization."""

    def test_client_wraps_provider(self, mock_provider):
        """Client should store provider reference."""
        client = WorkItemClient(mock_provider)
        assert client._provider == mock_provider

    def test_client_detects_capabilities(self, mock_provider):
        """Client should detect provider capabilities on init."""
        client = WorkItemClient(mock_provider)
        assert len(client.capabilities) > 0

    def test_provider_name(self, client, mock_provider):
        """Provider name should be accessible."""
        assert client.provider_name == "mock"


class TestWorkItemClientDelegation:
    """Test that client delegates to provider."""

    def test_get_work_item_delegates(self, client, mock_provider):
        """get_work_item should delegate to provider."""
        identity = WorkItemIdentity(provider="mock", external_id="1")
        result = client.get_work_item(identity)
        
        mock_provider.get_work_item.assert_called_once_with(identity)
        assert isinstance(result, WorkItem)

    def test_query_work_items_delegates(self, client, mock_provider):
        """query_work_items should delegate to provider."""
        query = WorkItemQuery()
        client.query_work_items(query)
        
        mock_provider.query_work_items.assert_called_once_with(query)

    def test_get_tags_delegates(self, client, mock_provider):
        """get_tags should delegate to provider."""
        identity = WorkItemIdentity(provider="mock", external_id="1")
        tags = client.get_tags(identity)
        
        mock_provider.get_tags.assert_called_once_with(identity)
        assert tags == ["tag1", "tag2"]

    def test_update_state_delegates(self, client, mock_provider):
        """update_state should delegate to provider."""
        identity = WorkItemIdentity(provider="mock", external_id="1")
        result = client.update_state(identity, WorkItemState.DESIGN_DRAFT)
        
        mock_provider.update_state.assert_called_once_with(identity, WorkItemState.DESIGN_DRAFT)
        assert result is True

    def test_post_comment_delegates(self, client, mock_provider):
        """post_comment should delegate to provider."""
        identity = WorkItemIdentity(provider="mock", external_id="1")
        result = client.post_comment(identity, "Test comment")
        
        mock_provider.post_comment.assert_called_once_with(identity, "Test comment")
        assert result is True

    def test_set_metadata_delegates(self, client, mock_provider):
        """set_metadata should delegate to provider."""
        identity = WorkItemIdentity(provider="mock", external_id="1")
        result = client.set_metadata(identity, "key", "value")
        
        mock_provider.set_metadata.assert_called_once_with(identity, "key", "value")
        assert result is True

    def test_add_tag_delegates(self, client, mock_provider):
        """add_tag should delegate to provider."""
        identity = WorkItemIdentity(provider="mock", external_id="1")
        result = client.add_tag(identity, "new-tag")
        
        mock_provider.add_tag.assert_called_once_with(identity, "new-tag")
        assert result is True

    def test_remove_tag_delegates(self, client, mock_provider):
        """remove_tag should delegate to provider."""
        identity = WorkItemIdentity(provider="mock", external_id="1")
        result = client.remove_tag(identity, "old-tag")
        
        mock_provider.remove_tag.assert_called_once_with(identity, "old-tag")
        assert result is True


class TestCapabilityDetection:
    """Test capability detection functions."""

    def test_detect_all_capabilities(self, mock_provider):
        """Full provider should have all capabilities."""
        caps = detect_capabilities(mock_provider)
        
        assert Capability.READ in caps
        assert Capability.WRITE_STATE in caps
        assert Capability.WRITE_COMMENT in caps
        assert Capability.WRITE_METADATA in caps
        assert Capability.WRITE_TAGS in caps

    def test_detect_missing_capability(self):
        """Provider missing methods should lack capability."""
        # Provider without update_state
        provider = Mock(spec=["name", "get_work_item", "query_work_items"])
        provider.name = "limited"
        
        caps = detect_capabilities(provider)
        
        assert Capability.READ in caps
        assert Capability.WRITE_STATE not in caps

    def test_has_capability_function(self, mock_provider):
        """has_capability should check correctly."""
        assert has_capability(mock_provider, Capability.READ) is True
        
    def test_has_capability_missing(self):
        """has_capability should return False for missing caps."""
        provider = Mock(spec=["name"])
        provider.name = "minimal"
        
        assert has_capability(provider, Capability.READ) is False

    def test_capability_methods_mapping(self):
        """CAPABILITY_METHODS should map correctly."""
        assert "get_work_item" in CAPABILITY_METHODS[Capability.READ]
        assert "update_state" in CAPABILITY_METHODS[Capability.WRITE_STATE]
        assert "post_comment" in CAPABILITY_METHODS[Capability.WRITE_COMMENT]


class TestWorkItemClientCapabilities:
    """Test client capability checking."""

    def test_client_has_capability(self, client):
        """Client should expose has_capability method."""
        assert client.has_capability(Capability.READ) is True

    def test_client_capabilities_property(self, client):
        """Client should expose capabilities set."""
        caps = client.capabilities
        assert isinstance(caps, set)
        assert len(caps) > 0


class TestWorkItemClientFactory:
    """Test client factory method."""

    def test_from_config_unknown_provider_raises(self):
        """Unknown provider should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            WorkItemClient._create_provider("unknown", {})
