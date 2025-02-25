from datetime import datetime
import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain.globals import set_debug
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import HumanMessage, SystemMessage
import requests.exceptions
from dotenv import load_dotenv
from github_getter import GitHubAnalyzer
from briefing_analyzer import ComplianceAnalyzer

class LLMClient:
    def __init__(
        self, 
        groq_api_key: Optional[str] = None,
        groq_model: str = "mixtral-8x7b-32768",
        ollama_model: str = "mistral:latest",
        logger: Optional[logging.Logger] = None
    ):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.groq_model = groq_model
        self.ollama_model = ollama_model
        self.logger = logger or logging.getLogger(__name__)
        self.using_ollama = False

        set_debug(True)
        self._initialize_llm()
        
    def _initialize_llm(self):
        try:
            if not self.groq_api_key:
                raise ValueError("No Groq API key provided")
                
            self.llm = ChatGroq(
                api_key=self.groq_api_key,
                model_name=self.groq_model,
                max_retries=0
            )
            self.using_ollama = False
            self.logger.info(f"Successfully initialized Groq model: {self.groq_model}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Groq: {e}. Falling back to Ollama")
            self._switch_to_ollama()
    
    def _switch_to_ollama(self) -> bool:
        try:
            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
            self.llm = Ollama(
                model=self.ollama_model,
                callback_manager=callback_manager
            )
            self.using_ollama = True
            self.logger.info(f"Switched to Ollama model: {self.ollama_model}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama: {e}")
            return False
    
    def invoke(self, messages: List) -> str:
        try:
            response = self.llm.invoke(messages)
            
            # Extract text content from response
            if self.using_ollama:
                return str(response).strip()
            else:
                if hasattr(response, 'content'):
                    return response.content.strip()
                elif isinstance(response, dict) and 'content' in response:
                    return response['content'].strip()
                elif isinstance(response, str):
                    return response.strip()
                else:
                    raise ValueError(f"Unexpected response format: {type(response)}")
                    
        except requests.exceptions.HTTPError as http_err:
            if hasattr(http_err.response, 'status_code') and http_err.response.status_code in [413, 429]:
                self.logger.warning(f"Groq API error {http_err.response.status_code}, switching to Ollama")
                if self._switch_to_ollama():
                    return self.invoke(messages)
            raise
        except Exception as e:
            self.logger.error(f"Error invoking LLM: {e}")
            if not self.using_ollama and self._switch_to_ollama():
                return self.invoke(messages)
            raise

class GitHubRAGAnalyzer:
    def __init__(
        self,
        model_name: str = "mixtral-8x7b-32768",
        api_key: str = None,
        ollama_model: str = 'mistral:latest'
    ):
        load_dotenv()
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.llm_client = LLMClient(
            groq_api_key=api_key,
            groq_model=model_name,
            ollama_model=ollama_model,
            logger=self.logger
        )
        self.github_analyzer = GitHubAnalyzer()
        self.compliance_analyzer = ComplianceAnalyzer()

    def analyze_requirements_completion(self, repo_url: str, briefing_path: str) -> Dict[str, Any]:
        try:
            # Get repository content
            repo_path = self.github_analyzer.clone_repo(repo_url)
            if not repo_path:
                raise ValueError("Failed to clone repository")

            repo_docs = self.github_analyzer.extract_text_from_repo(repo_path)
            if not repo_docs:
                raise ValueError("No content found in repository")
            
            # Get repository statistics
            repo_stats = self.github_analyzer.get_repo_stats(repo_url)
            
            # Get briefing content
            briefing_text = self.compliance_analyzer.extract_text_from_pdf(briefing_path)
            if not briefing_text:
                raise ValueError("Failed to extract briefing text")

            # Prepare content with length limit
            max_length = 4000 if not self.llm_client.using_ollama else 25000
            repo_content = "\n".join(repo_docs)[:max_length]
            
            # Generate analysis prompt
            prompt = f"""
            Eres un analista técnico especializado en proyectos de IA/ML.

            BRIEFING (Requisitos del proyecto):
            {briefing_text}

            CONTENIDO DEL REPOSITORIO:
            {repo_content}

            ESTADÍSTICAS DEL REPOSITORIO:
            {json.dumps(repo_stats, indent=2, ensure_ascii=False)}

            Por favor, analiza el repositorio y responde las siguientes preguntas:
            1. ¿Cumple el repositorio con los requisitos del briefing? ¿Por qué?
            2. ¿Qué requisitos o funcionalidades faltan por implementar?
            3. ¿Qué mejoras específicas recomiendas para el proyecto?

            Genera una respuesta en español, clara y concisa, en formato de párrafo.
            Enfócate en los aspectos positivos, negativos y recomendaciones de mejora.
            """

            # Get analysis from LLM
            messages = [
                SystemMessage(content="Eres un analista técnico que evalúa proyectos de IA en español."),
                HumanMessage(content=prompt)
            ]
            
            try:
                analysis = self.llm_client.invoke(messages)
                
                # Clean and encode the response
                cleaned_analysis = analysis.encode('utf-8', errors='ignore').decode('utf-8').strip()
                
                if not cleaned_analysis:
                    raise ValueError("Empty response after cleaning")
                    
                self.logger.info("Successfully generated analysis")
                
                # Return the response in the format expected by views.py
                return {
                    "project_type": "ml",  # Default to ML if not detected
                    "repository_stats": repo_stats,
                    "tier_analysis": {
                        "evaluacion_general": cleaned_analysis,
                        "analisis_por_nivel": {
                            "nivel_esencial": {
                                "requisitos_cumplidos": [],
                                "requisitos_faltantes": [],
                                "porcentaje_completitud": 0
                            }
                        },
                        "puntuacion_madurez": 0
                    },
                    "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "success"
                }
                
            except Exception as llm_error:
                self.logger.error(f"LLM analysis error: {llm_error}")
                raise ValueError(f"Error during LLM analysis: {str(llm_error)}")

        except Exception as e:
            self.logger.error(f"Error analyzing repository: {e}")
            return {
                "error": str(e),
                "repository": repo_url,
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "error"
            }