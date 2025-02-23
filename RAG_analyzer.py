from datetime import datetime
import os
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
import logging
from github_getter import GitHubAnalyzer
from briefing_analyzer import ComplianceAnalyzer

class GitHubRAGAnalyzer:
    def __init__(
        self,
        model_name: str = "mixtral-8x7b-32768",
        api_key: str = None
    ):
        """Initialize GitHub RAG Analyzer with Groq integration"""
        load_dotenv()
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("Groq API key required")
            
        self.github_analyzer = GitHubAnalyzer()
        self.compliance_analyzer = ComplianceAnalyzer()
        
        self.setup_logging()
        self.initialize_groq()

    def setup_logging(self):
        """Configure logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def initialize_groq(self):
        """Initialize Groq LLM"""
        self.llm = ChatGroq(
            api_key=self.api_key,
            model_name=self.model_name
        )

    def analyze_requirements_completion(self, repo_url: str, briefing_path: str) -> Dict[str, Any]:
        """
        Analyze repository compliance with briefing requirements
        
        Args:
            repo_url: GitHub repository URL
            briefing_path: Path to briefing PDF
            
        Returns:
            Dict containing analysis results and LLM-generated summary
        """
        try:
            # Get repository information
            repo_path = self.github_analyzer.clone_repo(repo_url)
            if not repo_path:
                raise ValueError("Failed to clone repository")

            repo_docs = self.github_analyzer.extract_text_from_repo(repo_path)
            repo_stats = self.github_analyzer.get_repo_stats(repo_url)
            
            # Get briefing analysis
            briefing_text = self.compliance_analyzer.extract_text_from_pdf(briefing_path)
            if not briefing_text:
                raise ValueError("Failed to extract briefing text")

            # Check compliance
            compliance_results = self.compliance_analyzer.check_compliance_with_briefing(
                repo_docs, 
                briefing_text
            )

            # Generate LLM analysis
            analysis = self._generate_compliance_analysis(
                briefing_text=briefing_text,
                repo_docs=repo_docs,
                compliance_results=compliance_results,
                repo_stats=repo_stats
            )

            return {
                "repository_stats": repo_stats,
                "compliance_results": compliance_results,
                "llm_analysis": analysis,
                "analysis_date": str(datetime.now())
            }

        except Exception as e:
            self.logger.error(f"Error in requirements analysis: {e}")
            return {
                "error": str(e),
                "analysis_date": str(datetime.now())
            }

    def _generate_compliance_analysis(
        self,
        briefing_text: str,
        repo_docs: List[str],
        compliance_results: List[Dict],
        repo_stats: Dict
    ) -> str:
        """Generate detailed analysis using Groq LLM"""
        try:
            prompt = f"""
            Analyze the following repository against briefing requirements:

            BRIEFING REQUIREMENTS:
            {briefing_text}

            REPOSITORY STATISTICS:
            - Total Commits: {repo_stats['commit_count']}
            - Contributors: {len(repo_stats['contributors'])}
            - Languages: {', '.join([f"{l['name']} ({l['percentage']}%)" for l in repo_stats['languages']])}

            COMPLIANCE RESULTS:
            {compliance_results}

            Please provide:
            1. Overall compliance assessment
            2. List of met requirements
            3. List of unmet requirements
            4. Recommendations for improvement
            5. Technical implementation analysis
            """

            messages = [
                SystemMessage(content="You are a technical project analyzer. Provide detailed analysis of project compliance with requirements."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content

        except Exception as e:
            self.logger.error(f"Error generating compliance analysis: {e}")
            return "Failed to generate analysis due to an error."
