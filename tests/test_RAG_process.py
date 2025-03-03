import pytest
from unittest.mock import MagicMock, patch
from langchain.schema.document import Document
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from RAG_process import RepoRAGProcessor

@pytest.fixture
def processor():
    """Create a processor with mocked dependencies"""
    # Create a processor without calling the real __init__
    with patch('RAG_process.RepoRAGProcessor.__init__', return_value=None):
        processor = RepoRAGProcessor()
        
    # Set up the object state directly
    processor.logger = MagicMock()
    processor.embeddings = MagicMock()
    processor.vector_store = None
    
    yield processor

def test_retrieve_relevant_content_no_vector_store(processor):
    """Test retrieve_relevant_content when vector_store is not initialized"""
    # Setup - vector_store is already None from fixture
    
    # Execute
    result = processor.retrieve_relevant_content("test query")
    
    # Verify
    assert result == []
    processor.logger.error.assert_called_once_with("Vector store not initialized")

def test_retrieve_relevant_content_success(processor):
    """Test retrieve_relevant_content when vector_store is initialized and working"""
    # Setup
    mock_doc1 = Document(page_content="Test content 1", metadata={"source": "test1.py", "type": "code"})
    mock_doc2 = Document(page_content="Test content 2", metadata={"source": "test2.py", "type": "code"})
    mock_docs = [mock_doc1, mock_doc2]
    
    processor.vector_store = MagicMock()
    processor.vector_store.similarity_search.return_value = mock_docs
    
    # Execute
    result = processor.retrieve_relevant_content("test query")
    
    # Verify
    assert result == mock_docs
    processor.vector_store.similarity_search.assert_called_once_with("test query", k=8)

def test_retrieve_relevant_content_k_parameter(processor):
    """Test retrieve_relevant_content handles k parameter correctly"""
    # Setup
    processor.vector_store = MagicMock()
    processor.vector_store.similarity_search.return_value = []
    
    # Execute
    result = processor.retrieve_relevant_content("test query", k=5)
    
    # Verify
    assert result == []
    processor.vector_store.similarity_search.assert_called_once_with("test query", k=5)

def test_retrieve_relevant_content_exception(processor):
    """Test retrieve_relevant_content when similarity_search raises an exception"""
    # Setup
    processor.vector_store = MagicMock()
    processor.vector_store.similarity_search.side_effect = Exception("Test error")
    
    # Execute
    result = processor.retrieve_relevant_content("test query")
    
    # Verify
    assert result == []
    processor.logger.error.assert_called_once()
    error_call_args = processor.logger.error.call_args[0][0]
    assert "Failed to retrieve content" in error_call_args
    assert "Test error" in error_call_args