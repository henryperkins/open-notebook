from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage, AIMessage


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app
    return TestClient(app)


class TestSourceChatRegenerate:
    """Test suite for Source Chat Regenerate endpoint."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    @patch("open_notebook.domain.notebook.ChatSession.get")
    @patch("api.routers.source_chat.repo_query")
    @patch("api.routers.source_chat.source_chat_graph")
    async def test_regenerate_success(self, mock_graph, mock_repo_query, mock_session_get, mock_source_get, client):
        """Test successful regeneration of AI response."""

        # Mock source exists
        mock_source = MagicMock()
        mock_source_get.return_value = mock_source

        # Mock session exists
        mock_session = MagicMock()
        mock_session.model_override = "gpt-4"
        mock_session_get.return_value = mock_session

        # Mock session-source relation exists
        mock_repo_query.return_value = [{"in": "chat_session:123", "out": "source:456"}]

        # Mock state history with most recent AI response first
        original_context = {"sources": ["source:456"], "insights": [], "notes": []}
        mock_snapshot_after_human = MagicMock()
        mock_snapshot_after_human.values = {
            "messages": [HumanMessage(content="Hello")],
            "context_indicators": original_context
        }
        mock_snapshot_after_human.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_human.metadata = {"step": 1}
        mock_snapshot_after_human.created_at = "2025-11-01T12:00:01Z"

        mock_snapshot_after_ai = MagicMock()
        mock_snapshot_after_ai.values = {
            "messages": [HumanMessage(content="Hello"), AIMessage(content="Old response")]
        }
        mock_snapshot_after_ai.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_ai.metadata = {"step": 2}
        mock_snapshot_after_ai.created_at = "2025-11-01T12:00:02Z"

        mock_graph.get_state_history.return_value = [
            mock_snapshot_after_ai,
            mock_snapshot_after_human
        ]

        # Mock update_state (for rollback)
        mock_graph.update_state.return_value = None

        # Mock graph invocation (for regeneration)
        mock_graph.invoke.return_value = {
            "messages": [HumanMessage(content="Hello"), AIMessage(content="New regenerated response")],
            "context_indicators": {"sources": ["source:456"], "insights": [], "notes": []}
        }

        # Mock session.save()
        mock_session.save = AsyncMock()

        response = client.post(
            "/api/sources/source456/chat/sessions/session123/messages/regenerate",
            json={"model_override": "gpt-4"}
        )

        assert response.status_code == 200

        # Verify rollback targeted the latest human-message checkpoint
        mock_graph.update_state.assert_called_once()
        update_kwargs = mock_graph.update_state.call_args.kwargs
        assert update_kwargs["config"] == mock_snapshot_after_human.config
        assert isinstance(update_kwargs["values"]["messages"][-1], HumanMessage)
        assert update_kwargs["values"]["context_indicators"] is None
        # Ensure original snapshot context indicators were not mutated
        assert mock_snapshot_after_human.values["context_indicators"] is original_context

        # Verify graph was invoked for regeneration
        mock_graph.invoke.assert_called_once()

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    @patch("open_notebook.domain.notebook.ChatSession.get")
    @patch("api.routers.source_chat.repo_query")
    @patch("api.routers.source_chat.source_chat_graph")
    async def test_regenerate_no_history(self, mock_graph, mock_repo_query, mock_session_get, mock_source_get, client):
        """Test regeneration when there's no AI response to regenerate."""

        # Mock source exists
        mock_source = MagicMock()
        mock_source_get.return_value = mock_source

        # Mock session exists
        mock_session = MagicMock()
        mock_session_get.return_value = mock_session

        # Mock session-source relation exists
        mock_repo_query.return_value = [{"in": "chat_session:123", "out": "source:456"}]

        # Mock state history that never ends with a human message
        mock_snapshot_only_ai = MagicMock()
        mock_snapshot_only_ai.values = {"messages": [AIMessage(content="Initial response")]}
        mock_snapshot_only_ai.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_only_ai.metadata = {"step": 0}
        mock_snapshot_only_ai.created_at = "2025-11-01T12:00:00Z"
        mock_graph.get_state_history.return_value = [mock_snapshot_only_ai]

        response = client.post(
            "/api/sources/source456/chat/sessions/session123/messages/regenerate",
            json={}
        )

        assert response.status_code == 409
        assert "Cannot regenerate: no previous AI response found" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    async def test_regenerate_source_not_found(self, mock_source_get, client):
        """Test regeneration when source doesn't exist."""

        # Mock source doesn't exist
        mock_source_get.return_value = None

        response = client.post(
            "/api/sources/nonexistent/chat/sessions/session123/messages/regenerate",
            json={}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Source not found"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    @patch("open_notebook.domain.notebook.ChatSession.get")
    @patch("api.routers.source_chat.repo_query")
    async def test_regenerate_session_not_found(self, mock_repo_query, mock_session_get, mock_source_get, client):
        """Test regeneration when session doesn't exist."""

        # Mock source exists
        mock_source = MagicMock()
        mock_source_get.return_value = mock_source

        # Mock session doesn't exist
        mock_session_get.return_value = None

        response = client.post(
            "/api/sources/source456/chat/sessions/nonexistent/messages/regenerate",
            json={}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    @patch("open_notebook.domain.notebook.ChatSession.get")
    @patch("api.routers.source_chat.repo_query")
    async def test_regenerate_session_not_related_to_source(self, mock_repo_query, mock_session_get, mock_source_get, client):
        """Test regeneration when session exists but isn't related to the source."""

        # Mock source exists
        mock_source = MagicMock()
        mock_source_get.return_value = mock_source

        # Mock session exists
        mock_session = MagicMock()
        mock_session_get.return_value = mock_session

        # Mock no relation between session and source
        mock_repo_query.return_value = []

        response = client.post(
            "/api/sources/source456/chat/sessions/session123/messages/regenerate",
            json={}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found for this source"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    @patch("open_notebook.domain.notebook.ChatSession.get")
    @patch("api.routers.source_chat.repo_query")
    @patch("api.routers.source_chat.source_chat_graph")
    async def test_regenerate_with_model_override(self, mock_graph, mock_repo_query, mock_session_get, mock_source_get, client):
        """Test regeneration with model override that takes precedence over session override."""

        # Mock source exists
        mock_source = MagicMock()
        mock_source_get.return_value = mock_source

        # Mock session exists with different model override
        mock_session = MagicMock()
        mock_session.model_override = "gpt-3.5-turbo"
        mock_session_get.return_value = mock_session

        # Mock session-source relation exists
        mock_repo_query.return_value = [{"in": "chat_session:123", "out": "source:456"}]

        # Mock state history
        mock_snapshot_after_human = MagicMock()
        mock_snapshot_after_human.values = {"messages": [HumanMessage(content="Hello")]}
        mock_snapshot_after_human.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_human.metadata = {"step": 1}
        mock_snapshot_after_human.created_at = "2025-11-01T12:00:01Z"

        mock_snapshot_after_ai = MagicMock()
        mock_snapshot_after_ai.values = {"messages": [HumanMessage(content="Hello"), AIMessage(content="Old response")]}
        mock_snapshot_after_ai.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_ai.metadata = {"step": 2}
        mock_snapshot_after_ai.created_at = "2025-11-01T12:00:02Z"

        mock_graph.get_state_history.return_value = [mock_snapshot_after_ai, mock_snapshot_after_human]
        mock_graph.update_state.return_value = None
        mock_graph.invoke.return_value = {
            "messages": [HumanMessage(content="Hello"), AIMessage(content="New response with Claude")],
            "context_indicators": {"sources": [], "insights": [], "notes": []}
        }

        # Mock session.save()
        mock_session.save = AsyncMock()

        response = client.post(
            "/api/sources/source456/chat/sessions/session123/messages/regenerate",
            json={"model_override": "claude-3-sonnet"}
        )

        assert response.status_code == 200

        # Verify graph was invoked with the override model (not session model)
        mock_graph.invoke.assert_called_once()
        call_args = mock_graph.invoke.call_args
        assert "config" in call_args.kwargs
        assert call_args.kwargs["config"]["configurable"]["model_id"] == "claude-3-sonnet"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    @patch("open_notebook.domain.notebook.ChatSession.get")
    @patch("api.routers.source_chat.repo_query")
    @patch("api.routers.source_chat.source_chat_graph")
    async def test_regenerate_uses_session_model_when_no_override(self, mock_graph, mock_repo_query, mock_session_get, mock_source_get, client):
        """Test regeneration uses session model override when no request override."""

        # Mock source exists
        mock_source = MagicMock()
        mock_source_get.return_value = mock_source

        # Mock session exists with model override
        mock_session = MagicMock()
        mock_session.model_override = "gpt-4"
        mock_session_get.return_value = mock_session

        # Mock session-source relation exists
        mock_repo_query.return_value = [{"in": "chat_session:123", "out": "source:456"}]

        # Mock state history
        mock_snapshot_after_human = MagicMock()
        mock_snapshot_after_human.values = {"messages": [HumanMessage(content="Hello")]}
        mock_snapshot_after_human.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_human.metadata = {"step": 1}
        mock_snapshot_after_human.created_at = "2025-11-01T12:00:01Z"

        mock_snapshot_after_ai = MagicMock()
        mock_snapshot_after_ai.values = {"messages": [HumanMessage(content="Hello"), AIMessage(content="Old response")]}
        mock_snapshot_after_ai.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_ai.metadata = {"step": 2}
        mock_snapshot_after_ai.created_at = "2025-11-01T12:00:02Z"

        mock_graph.get_state_history.return_value = [mock_snapshot_after_ai, mock_snapshot_after_human]
        mock_graph.update_state.return_value = None
        mock_graph.invoke.return_value = {
            "messages": [HumanMessage(content="Hello"), AIMessage(content="New response")],
            "context_indicators": {"sources": [], "insights": [], "notes": []}
        }

        # Mock session.save()
        mock_session.save = AsyncMock()

        response = client.post(
            "/api/sources/source456/chat/sessions/session123/messages/regenerate",
            json={}  # No model override in request
        )

        assert response.status_code == 200

        # Verify graph was invoked with session model
        mock_graph.invoke.assert_called_once()
        call_args = mock_graph.invoke.call_args
        assert "config" in call_args.kwargs
        assert call_args.kwargs["config"]["configurable"]["model_id"] == "gpt-4"

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.Source.get")
    @patch("open_notebook.domain.notebook.ChatSession.get")
    @patch("api.routers.source_chat.repo_query")
    @patch("api.routers.source_chat.source_chat_graph")
    async def test_regenerate_clears_context_indicators(self, mock_graph, mock_repo_query, mock_session_get, mock_source_get, client):
        """Test that context indicators are cleared in rollback snapshot."""

        # Mock source exists
        mock_source = MagicMock()
        mock_source_get.return_value = mock_source

        # Mock session exists
        mock_session = MagicMock()
        mock_session_get.return_value = mock_session

        # Mock session-source relation exists
        mock_repo_query.return_value = [{"in": "chat_session:123", "out": "source:456"}]

        # Mock state history where rollback snapshot has context indicators
        original_context = {"sources": ["source:456"], "insights": [], "notes": []}
        mock_snapshot_after_human = MagicMock()
        mock_snapshot_after_human.values = {
            "messages": [HumanMessage(content="Hello")],
            "context_indicators": original_context
        }
        mock_snapshot_after_human.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_human.metadata = {"step": 1}
        mock_snapshot_after_human.created_at = "2025-11-01T12:00:01Z"

        mock_snapshot_after_ai = MagicMock()
        mock_snapshot_after_ai.values = {"messages": [HumanMessage(content="Hello"), AIMessage(content="Old response")]}
        mock_snapshot_after_ai.config = {"configurable": {"thread_id": "session123"}}
        mock_snapshot_after_ai.metadata = {"step": 2}
        mock_snapshot_after_ai.created_at = "2025-11-01T12:00:02Z"

        mock_graph.get_state_history.return_value = [mock_snapshot_after_ai, mock_snapshot_after_human]
        mock_graph.update_state.return_value = None
        mock_graph.invoke.return_value = {
            "messages": [HumanMessage(content="Hello"), AIMessage(content="New response")],
            "context_indicators": {"sources": ["source:456"], "insights": [], "notes": []}  # Fresh indicators
        }

        # Mock session.save()
        mock_session.save = AsyncMock()

        response = client.post(
            "/api/sources/source456/chat/sessions/session123/messages/regenerate",
            json={}
        )

        assert response.status_code == 200

        # Verify context indicators were cleared in rollback snapshot
        call_args = mock_graph.update_state.call_args
        assert call_args.kwargs["values"]["context_indicators"] is None
        # Ensure the stored history wasn't mutated
        assert mock_snapshot_after_human.values["context_indicators"] is original_context
