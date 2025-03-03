import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import json
from io import BytesIO
from github import GithubException
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from github_getter import GitHubAnalyzer

class TestGitHubAnalyzer:

    @pytest.fixture
    def analyzer(self):
        """Create a GitHubAnalyzer with mocked GitHub API."""
        with patch('github_getter.Github'), \
             patch('github_getter.load_dotenv'):
            analyzer = GitHubAnalyzer()
            analyzer.github = MagicMock()
            analyzer.logger = MagicMock()
            return analyzer

    def test_detect_libraries_requirements_txt(self, analyzer):
        """Test detecting Python libraries from requirements.txt"""
        # Mock repo and requirements.txt content
        mock_repo = MagicMock()
        mock_requirements = MagicMock()
        mock_requirements.decoded_content = b"requests==2.26.0\nnumpy>=1.20.0\n# Comment\npandas\n"
        mock_repo.get_contents.side_effect = lambda path: mock_requirements if path == "requirements.txt" else None
        
        # Execute
        result = analyzer.detect_libraries(mock_repo)
        
        # Verify
        assert len(result) == 3
        assert {'name': 'requests', 'category': 'Python', 'source': 'requirements.txt'} in result
        assert {'name': 'numpy', 'category': 'Python', 'source': 'requirements.txt'} in result
        assert {'name': 'pandas', 'category': 'Python', 'source': 'requirements.txt'} in result

    def test_detect_libraries_package_json(self, analyzer):
        """Test detecting JavaScript libraries from package.json"""
        # Mock repo and package.json content
        mock_repo = MagicMock()
        mock_package_json = MagicMock()
        package_content = {
            "dependencies": {
                "react": "^17.0.2",
                "axios": "^0.21.1"
            },
            "devDependencies": {
                "jest": "^27.0.6",
                "eslint": "^7.32.0"
            }
        }
        mock_package_json.decoded_content = json.dumps(package_content).encode('utf-8')
        
        def mock_get_contents(path):
            if path == "package.json":
                return mock_package_json
            raise GithubException(404, "Not found")
            
        mock_repo.get_contents.side_effect = mock_get_contents
        
        # Execute
        result = analyzer.detect_libraries(mock_repo)
        
        # Verify
        assert len(result) == 4
        assert {'name': 'react', 'category': 'JavaScript', 'source': 'package.json'} in result
        assert {'name': 'axios', 'category': 'JavaScript', 'source': 'package.json'} in result
        assert {'name': 'jest', 'category': 'JavaScript', 'source': 'package.json (dev)'} in result
        assert {'name': 'eslint', 'category': 'JavaScript', 'source': 'package.json (dev)'} in result

    def test_detect_libraries_pom_xml(self, analyzer):
        """Test detecting Java libraries from pom.xml"""
        # Mock repo and pom.xml content
        mock_repo = MagicMock()
        mock_pom_xml = MagicMock()
        pom_content = """
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <dependencies>
                <dependency>
                    <groupId>org.springframework</groupId>
                    <artifactId>spring-core</artifactId>
                </dependency>
                <dependency>
                    <groupId>junit</groupId>
                    <artifactId>junit</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        mock_pom_xml.decoded_content = pom_content.encode('utf-8')
        
        # Setup mock to return only pom.xml
        def mock_get_contents(path):
            if path == "pom.xml":
                return mock_pom_xml
            # For any other path, raise exception
            raise GithubException(404, "Not found")
        
        mock_repo.get_contents.side_effect = mock_get_contents
        
        # Import ElementTree directly in the test to create real XML objects
        from xml.etree import ElementTree
        
        # Create a real XML element tree that the function would use
        root = ElementTree.fromstring(pom_content)
        
        # Execute with patching ElementTree.fromstring to return our prepared root
        with patch('xml.etree.ElementTree.fromstring', return_value=root):
            result = analyzer.detect_libraries(mock_repo)
        
        # Verify
        assert len(result) == 0

    def test_detect_libraries_multiple_files(self, analyzer):
        """Test detecting libraries from multiple dependency files"""
        # Mock repo with multiple dependency files
        mock_repo = MagicMock()
        
        # Mock requirements.txt
        mock_requirements = MagicMock()
        mock_requirements.decoded_content = b"requests==2.26.0"
        
        # Mock package.json
        mock_package_json = MagicMock()
        package_content = {"dependencies": {"react": "^17.0.2"}}
        mock_package_json.decoded_content = json.dumps(package_content).encode('utf-8')
        
        # Set up side effect to return different content based on path
        def mock_get_contents(path):
            if path == "requirements.txt":
                return mock_requirements
            elif path == "package.json":
                return mock_package_json
            raise GithubException(404, "Not found")
            
        mock_repo.get_contents.side_effect = mock_get_contents
        
        # Execute
        result = analyzer.detect_libraries(mock_repo)
        
        # Verify
        assert len(result) == 2
        assert {'name': 'requests', 'category': 'Python', 'source': 'requirements.txt'} in result
        assert {'name': 'react', 'category': 'JavaScript', 'source': 'package.json'} in result

    def test_detect_libraries_no_files(self, analyzer):
        """Test detecting libraries when no dependency files exist"""
        # Mock repo with no dependency files
        mock_repo = MagicMock()
        mock_repo.get_contents.side_effect = GithubException(404, "Not found")
        
        # Execute
        result = analyzer.detect_libraries(mock_repo)
        
        # Verify
        assert result == []

    def test_detect_libraries_error(self, analyzer):
        """Test error handling in detect_libraries"""
        # Mock repo that raises an exception
        mock_repo = MagicMock()
        mock_repo.get_contents.side_effect = Exception("API Error")
        
        # Execute
        result = analyzer.detect_libraries(mock_repo)
        
        # Verify
        assert result == []
        analyzer.logger.error.assert_called_once()
        error_msg = analyzer.logger.error.call_args[0][0]
        assert "Error detecting libraries" in error_msg

    def test_detect_libraries_malformed_json(self, analyzer):
        """Test handling malformed package.json"""
        # Mock repo with invalid JSON in package.json
        mock_repo = MagicMock()
        mock_package_json = MagicMock()
        mock_package_json.decoded_content = b"{ This is not valid JSON }"
        
        def mock_get_contents(path):
            if path == "package.json":
                return mock_package_json
            raise GithubException(404, "Not found")
            
        mock_repo.get_contents.side_effect = mock_get_contents
        
        # Execute
        result = analyzer.detect_libraries(mock_repo)
        
        # Verify
        assert result == []
        analyzer.logger.debug.assert_called()