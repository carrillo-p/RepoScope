import pytest
from unittest.mock import MagicMock, patch, ANY
import os
import json
from datetime import datetime
import requests
from requests import HTTPError as http_error
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from RAG_analyzer import LLMClient, GitHubRAGAnalyzer
from briefing_analyzer import ComplianceAnalyzer

class TestLLMClient:
    
    @pytest.fixture
    def mock_logger(self):
        return MagicMock()
    
    @patch('RAG_analyzer.ChatGroq')
    def test_init_with_groq_api_key(self, mock_chat_groq, mock_logger):
        # Test successful initialization with Groq API key
        client = LLMClient(groq_api_key="test_api_key", logger=mock_logger)
        
        # Verify Groq was initialized
        mock_chat_groq.assert_called_once_with(
            api_key="test_api_key", 
            model_name="mixtral-8x7b-32768",
            max_retries=0
        )
        assert not client.using_ollama
        mock_logger.info.assert_called_with(ANY)
    
    @patch('RAG_analyzer.ChatGroq')
    @patch('RAG_analyzer.Ollama')
    def test_groq_failure_fallback_to_ollama(self, mock_ollama, mock_chat_groq, mock_logger):
        # Simulate Groq initialization failure
        mock_chat_groq.side_effect = Exception("Groq API key invalid")
        
        # Initialize client
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://test-ollama:11434"}):
            client = LLMClient(groq_api_key="invalid_key", logger=mock_logger)
        
        # Verify fallback to Ollama
        mock_ollama.assert_called_once()
        assert client.using_ollama
        mock_logger.warning.assert_called_once()
    
    @patch('RAG_analyzer.ChatGroq')
    @patch('RAG_analyzer.Ollama')
    def test_switch_to_ollama_success(self, mock_ollama, mock_chat_groq, mock_logger):
        # Create client first with Groq
        client = LLMClient(groq_api_key="test_key", logger=mock_logger)
        client.using_ollama = False
        
        # Reset mock to test _switch_to_ollama
        mock_logger.reset_mock()
        
        # Call _switch_to_ollama
        result = client._switch_to_ollama()
        
        # Verify
        assert result is True
        assert client.using_ollama is True
        mock_logger.info.assert_called_with(ANY)
    
    @patch('RAG_analyzer.Ollama')
    def test_switch_to_ollama_error(self, mock_ollama, mock_logger):
        # Setup Ollama to fail
        mock_ollama.side_effect = Exception("Connection refused")
        
        # Create client
        client = LLMClient(groq_api_key=None, logger=mock_logger)
        client.using_ollama = False
        
        # Reset mock to test _switch_to_ollama
        mock_logger.reset_mock()
        
        # Call _switch_to_ollama
        result = client._switch_to_ollama()
        
        # Verify
        assert result is False
        mock_logger.error.assert_called_once()
    
    def test_invoke_ollama_response(self, mock_logger):
        # Create client with mocked LLM
        client = LLMClient(groq_api_key=None, logger=mock_logger)
        client.using_ollama = True
        client.llm = MagicMock()
        client.llm.invoke.return_value = "Ollama response"
        
        # Call invoke
        response = client.invoke([{"role": "user", "content": "test"}])
        
        # Verify
        assert response == "Ollama response"
    
    def test_invoke_groq_response_attribute(self, mock_logger):
        # Create client with mocked LLM returning object with content attribute
        client = LLMClient(groq_api_key="test_key", logger=mock_logger)
        client.using_ollama = False
        client.llm = MagicMock()
        
        mock_response = MagicMock()
        mock_response.content = "Groq response"
        client.llm.invoke.return_value = mock_response
        
        # Call invoke
        response = client.invoke([{"role": "user", "content": "test"}])
        
        # Verify
        assert response == "Groq response"
    
    def test_invoke_groq_response_dict(self, mock_logger):
        # Create client with mocked LLM returning dict with content key
        client = LLMClient(groq_api_key="test_key", logger=mock_logger)
        client.using_ollama = False
        client.llm = MagicMock()
        client.llm.invoke.return_value = {"content": "Groq dict response"}
        
        # Call invoke
        response = client.invoke([{"role": "user", "content": "test"}])
        
        # Verify
        assert response == "Groq dict response"
    
    def test_invoke_http_error_fallback(self, mock_logger):
        # Create client
        client = LLMClient(groq_api_key="test_key", logger=mock_logger)
        
        # Setup primary LLM to raise an HTTP error
        client.llm = MagicMock()
        
        http_error = requests.exceptions.HTTPError("API error")
        http_error.response = MagicMock()
        http_error.response.status_code = 429

        def raise_http_error(*args, **kwargs):
            raise http_error
        
        client.llm.invoke.side_effect = raise_http_error

        # Mock the fallback behavior
        client.using_ollama = False
        
        def switch_mock():
            client.using_ollama = True
            # Replace the LLM with one that works
            client.llm = MagicMock()
            client.llm.invoke.return_value = "Fallback response"
            return True
        
        client._switch_to_ollama = MagicMock(side_effect=switch_mock)
        
        # Call invoke
        response = client.invoke([{"role": "user", "content": "test"}])
        
        # Verify
        assert response == "Fallback response"
        client._switch_to_ollama.assert_called_once()


class TestGitHubRAGAnalyzer:
    
    @pytest.fixture
    def mock_logger(self):
        return MagicMock()
    
    @pytest.fixture
    def analyzer(self, mock_logger):
        with patch('RAG_analyzer.LLMClient'), \
             patch('RAG_analyzer.GitHubAnalyzer'), \
             patch('RAG_analyzer.ComplianceAnalyzer'), \
             patch('RAG_analyzer.RepoRAGProcessor'), \
             patch('RAG_analyzer.load_dotenv'):
            
            # Create analyzer instance
            analyzer = GitHubRAGAnalyzer(
                model_name="test-model",
                api_key="test-key",
                ollama_model="test-ollama-model"
            )
            
            # Configure mocks
            analyzer.logger = mock_logger
            analyzer.llm_client = MagicMock()
            analyzer.github_analyzer = MagicMock()
            analyzer.compliance_analyzer = MagicMock()
            analyzer.rag_processor = MagicMock()
            
            return analyzer
    
    def test_initialization(self):
        # Test initialization with all components properly set up
        with patch('RAG_analyzer.LLMClient') as mock_llm, \
             patch('RAG_analyzer.GitHubAnalyzer') as mock_github, \
             patch('RAG_analyzer.ComplianceAnalyzer') as mock_compliance, \
             patch('RAG_analyzer.RepoRAGProcessor') as mock_rag, \
             patch('RAG_analyzer.load_dotenv'):
            
            analyzer = GitHubRAGAnalyzer(
                model_name="test-model",
                api_key="test-key",
                ollama_model="test-ollama-model",
                embedding_model="test-embedding-model"
            )
            
            # Verify proper initialization
            mock_llm.assert_called_once_with(
                groq_api_key="test-key",
                groq_model="test-model",
                ollama_model="test-ollama-model",
                logger=analyzer.logger
            )
            mock_github.assert_called_once()
            mock_compliance.assert_called_once()
            mock_rag.assert_called_once_with(embedding_model_name="test-embedding-model")
    
    def test_analyze_requirements_completion_success(self, analyzer):
        # Mock repository cloning
        analyzer.github_analyzer.clone_repo.return_value = "/path/to/cloned/repo"
        
        # Mock repository processing
        analyzer.rag_processor.process_repository.return_value = True
        
        # Mock briefing file existence and processing
        with patch('RAG_analyzer.os.path.exists', return_value=True):
            analyzer.compliance_analyzer = MagicMock()
            analyzer.rag_processor.process_briefing.return_value = True
        
            # Mock repository stats and technologies
            analyzer.github_analyzer.get_repo_stats.return_value = {"stars": 10, "forks": 5}
            analyzer.rag_processor.technologies = {"python": 80, "javascript": 20}
            
            # Mock RAG context retrieval
            analyzer.rag_processor.get_formatted_context.return_value = "Formatted context"
            
            # Mock LLM response
            analyzer.llm_client.invoke.return_value = (
                "# 1. Análisis Técnico Multinivel\nContent here\n"
                "## 2. Niveles de Objetivos Alcanzados\nMore content\n"
                "### 3. Uso de IA y Señales de Alerta Pedagógica\nEven more content\n"
                "#### 4. Mejoras Priorizadas para Madurez Técnica\nAdditional content\n"
                "##### 5. Elementos para Revisión Docente\nFinal content"
            )
            
            # Call method
            result = analyzer.analyze_requirements_completion(
                repo_url="https://github.com/user/repo",
                briefing_path="/path/to/briefing.pdf"
            )
        
        # Verify successful flow
        assert result["status"] == "success"
        assert "evaluacion_general" in result["tier_analysis"]
    
    def test_analyze_requirements_completion_missing_sections(self, analyzer):
        # Mock repository cloning and processing success
        analyzer.github_analyzer.clone_repo.return_value = "/path/to/cloned/repo"
        analyzer.rag_processor.process_repository.return_value = True
        
        # Mock briefing file existence and processing - using correct import path
        with patch('RAG_analyzer.os.path.exists', return_value=True):
            analyzer.rag_processor.process_briefing.return_value = True
        
            # Mock repository stats and technologies
            analyzer.github_analyzer.get_repo_stats.return_value = {"stars": 10, "forks": 5}
            analyzer.rag_processor.technologies = {"python": 80, "javascript": 20}
            
            # Mock RAG context retrieval
            analyzer.rag_processor.get_formatted_context.return_value = "Formatted context"
            
            # Mock LLM response with missing sections
            analyzer.llm_client.invoke.return_value = (
                "# 1. Análisis Técnico Multinivel\n"
                "Content here\n"
                "## 2. Niveles de Objetivos Alcanzados\n"
                "More content\n"
                # Missing sections 3, 4, 5
            )
            
            # Call method
            result = analyzer.analyze_requirements_completion(
                repo_url="https://github.com/user/repo",
                briefing_path="/path/to/briefing.pdf"
            )
        
        # Verify successful flow and added missing sections
        assert result["status"] == "success"
        assert "3. Uso de IA y Señales de Alerta Pedagógica" in result["tier_analysis"]["evaluacion_general"]
    
    def test_analyze_requirements_completion_clone_error(self, analyzer):
        # Mock repository cloning failure
        analyzer.github_analyzer.clone_repo.return_value = None
        
        # Call method
        result = analyzer.analyze_requirements_completion(
            repo_url="https://github.com/user/repo",
            briefing_path="/path/to/briefing.pdf"
        )
        
        # Verify error handling
        assert result["status"] == "error"
        assert "Failed to clone repository" in result["error"]
        analyzer.logger.error.assert_called()
    
    def test_analyze_requirements_completion_repo_processing_error(self, analyzer):
        # Mock repository cloning success but processing failure
        analyzer.github_analyzer.clone_repo.return_value = "/path/to/cloned/repo"
        analyzer.rag_processor.process_repository.return_value = False
        
        # Call method
        result = analyzer.analyze_requirements_completion(
            repo_url="https://github.com/user/repo",
            briefing_path="/path/to/briefing.pdf"
        )
        
        # Verify error handling
        assert result["status"] == "error"
        assert "Failed to process repository content" in result["error"]
    
    def test_analyze_requirements_completion_briefing_not_found(self, analyzer):
        # Mock repository cloning and processing success
        analyzer.github_analyzer.clone_repo.return_value = "/path/to/cloned/repo"
        analyzer.rag_processor.process_repository.return_value = True
        
        # Mock briefing file not existing
        with patch('os.path.exists', return_value=False):
            # Call method
            result = analyzer.analyze_requirements_completion(
                repo_url="https://github.com/user/repo",
                briefing_path="/path/to/briefing.pdf"
            )
        
        # Verify error handling
        assert result["status"] == "error"
        assert "Briefing file not found" in result["error"]
    
    def test_analyze_requirements_completion_briefing_processing_error(self, analyzer):
        # Mock repository cloning and processing success
        analyzer.github_analyzer.clone_repo.return_value = "/path/to/cloned/repo"
        analyzer.rag_processor.process_repository.return_value = True
        
        # Mock briefing file exists but processing fails
        with patch('os.path.exists', return_value=True):
            analyzer.rag_processor.process_briefing.return_value = False
            
            # Call method
            result = analyzer.analyze_requirements_completion(
                repo_url="https://github.com/user/repo",
                briefing_path="/path/to/briefing.pdf"
            )
        
        # Verify error handling
        assert result["status"] == "error"
        assert "Failed to process briefing document" in result["error"]
    
    def test_analyze_requirements_completion_llm_error(self, analyzer):
        # Mock repository cloning and processing success
        analyzer.github_analyzer.clone_repo.return_value = "/path/to/cloned/repo"
        analyzer.rag_processor.process_repository.return_value = True
        
        # Mock briefing file exists and processes successfully
        with patch('RAG_analyzer.os.path.exists', return_value=True):
            analyzer.rag_processor.process_briefing.return_value = True
        
            # Mock repository stats and technologies
            analyzer.github_analyzer.get_repo_stats.return_value = {"stars": 10, "forks": 5}
            analyzer.rag_processor.technologies = {"python": 80, "javascript": 20}
            
            # Mock RAG context retrieval
            analyzer.rag_processor.get_formatted_context.return_value = "Formatted context"
            
            # Mock LLM error
            analyzer.llm_client.invoke.side_effect = Exception("LLM error")
            
            # Call method
            result = analyzer.analyze_requirements_completion(
                repo_url="https://github.com/user/repo",
                briefing_path="/path/to/briefing.pdf"
            )
        
        # Verify error handling
        assert result["status"] == "error"
        assert "Error during LLM analysis" in result["error"]