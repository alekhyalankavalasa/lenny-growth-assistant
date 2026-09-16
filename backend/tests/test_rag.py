import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.rag.retrieval import retrieve

@pytest.mark.asyncio
@patch('app.rag.retrieval.get_embedder')
async def test_retrieve_empty_results(mock_get_embedder):
    # Mock embedder
    mock_embedder = MagicMock()
    mock_embedder.embed = AsyncMock(return_value=[[0.1] * 384])
    mock_get_embedder.return_value = mock_embedder

    # Mock DB session
    mock_db = AsyncMock()
    
    # Mock execute results to be empty
    mock_result = MagicMock()
    mock_result.mappings().all.return_value = []
    mock_db.execute.return_value = mock_result

    results = await retrieve("test query", mock_db)
    
    assert results == []

@pytest.mark.asyncio
@patch('app.rag.retrieval.get_embedder')
async def test_retrieve_with_results(mock_get_embedder):
    # Mock embedder
    mock_embedder = MagicMock()
    mock_embedder.embed = AsyncMock(return_value=[[0.1] * 384])
    mock_get_embedder.return_value = mock_embedder

    # Mock DB session
    mock_db = AsyncMock()
    
    # Mock execute results
    mock_row = {
        "id": "1",
        "episode_title": "Test Title",
        "source_file": "test.md",
        "source_type": "podcast",
        "chunk_index": 0,
        "content": "This is a test chunk content that should be retrieved."
    }
    
    mock_result = MagicMock()
    mock_result.mappings().all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    results = await retrieve("test query", mock_db)
    
    assert len(results) == 1
    assert results[0]["episode_title"] == "Test Title"
    assert "This is a test chunk" in results[0]["excerpt"]
