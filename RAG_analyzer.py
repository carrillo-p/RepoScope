from datetime import datetime
import os
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
import logging
from github_getter import GitHubAnalyzer
from briefing_analyzer import ComplianceAnalyzer
import json
from tenacity import retry, stop_after_attempt, wait_exponential
import sys

root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

class GitHubRAGAnalyzer:
    """
    Clase principal para analizar repositorios de GitHub usando RAG (Retrieval Augmented Generation)
    y evaluarlos contra requisitos específicos de proyectos de IA
    """
    def __init__(
        self,
        model_name: str = "mixtral-8x7b-32768",
        api_key: str = None
    ):
        """
        Inicialización del analizador con integración de Groq
        Args:
            model_name: Nombre del modelo de Groq a utilizar
            api_key: Clave API de Groq (opcional, puede estar en .env)
        """
        load_dotenv()
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("Groq API key required")
            
        # Inicialización de componentes principales
        self.github_analyzer = GitHubAnalyzer()
        self.compliance_analyzer = ComplianceAnalyzer()
        
        self.setup_logging()
        self.initialize_groq()
        self.setup_prompts()
        self.project_type = None  # Se establecerá durante el análisis

    def setup_logging(self):
        """Configuración del sistema de logging para seguimiento y depuración"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def initialize_groq(self):
        """Inicialización del modelo de lenguaje Groq"""
        self.llm = ChatGroq(
            api_key=self.api_key,
            model_name=self.model_name
        )

    def detect_project_type(self, briefing_text: str) -> str:
        """
        Detecta el tipo de proyecto a partir del contenido del briefing
        Args:
            briefing_text: Texto del briefing a analizar
        Returns:
            str: Tipo de proyecto ('ml', 'nlp', o 'genai')
        """
        try:
            # Prompt para la detección del tipo de proyecto
            prompt = """
            Analiza el siguiente texto de briefing y determina el tipo de proyecto.
            Clasifica entre: 'ml' (Machine Learning), 'nlp' (Procesamiento de Lenguaje Natural), 
            o 'genai' (IA Generativa).

            TEXTO DEL BRIEFING:
            {text}

            Responde solo con el identificador correspondiente: 'ml', 'nlp', o 'genai'.
            """

            messages = [
                SystemMessage(content="Eres un analista técnico especializado en detectar tipos de proyectos de IA."),
                HumanMessage(content=prompt.format(text=briefing_text))
            ]
            
            response = self.llm.invoke(messages)
            project_type = response.content.strip().lower()
            
            # Validación del tipo de proyecto
            if project_type not in ['ml', 'nlp', 'genai']:
                self.logger.warning(f"Tipo de proyecto no reconocido: {project_type}. Usando 'ml' por defecto.")
                return 'ml'
                
            return project_type

        except Exception as e:
            self.logger.error(f"Error detecting project type: {e}")
            return 'ml'
    
    def setup_prompts(self):
        """
        Configura las descripciones de los niveles de competencia según el tipo de proyecto
        Establece criterios específicos para cada nivel y tipo de proyecto
        """
        self.tier_descriptions = {
            "nivel_esencial": {
                "ml": "Funcionalidad básica de machine learning (preprocesamiento, entrenamiento, evaluación)",
                "nlp": "Procesamiento básico de texto y análisis lingüístico",
                "genai": "Generación básica de contenido con modelos pre-entrenados"
            },
            "nivel_medio": {
                "ml": "Optimización de modelos, validación cruzada, pipeline de datos",
                "nlp": "Análisis semántico, embeddings, clasificación de texto",
                "genai": "Fine-tuning de modelos, prompting avanzado"
            },
            "nivel_avanzado": {
                "ml": "Arquitecturas complejas, experimentación sistemática, MLOps",
                "nlp": "Modelos transformer personalizados, análisis multilingüe",
                "genai": "Modelos personalizados, control de sesgos, evaluación"
            },
            "nivel_experto": {
                "ml": "Innovación en arquitecturas, optimización distribuida",
                "nlp": "Investigación en NLP, modelos state-of-the-art",
                "genai": "Arquitecturas innovadoras, seguridad y ética"
            }
        }

    def analyze_requirements_completion(self, repo_url: str, briefing_path: str) -> Dict[str, Any]:
        """
        Analiza un repositorio contra los requisitos del briefing
        Args:
            repo_url: URL del repositorio a analizar
            briefing_path: Ruta al archivo del briefing
        Returns:
            Dict: Resultados del análisis
        """
        try:
            # Obtención de información del repositorio
            repo_path = self.github_analyzer.clone_repo(repo_url)
            if not repo_path:
                raise ValueError("Failed to clone repository")

            repo_docs = self.github_analyzer.extract_text_from_repo(repo_path)
            repo_stats = self.github_analyzer.get_repo_stats(repo_url)
            
            # Extracción del briefing y detección del tipo de proyecto
            briefing_text = self.compliance_analyzer.extract_text_from_pdf(briefing_path)
            if not briefing_text:
                raise ValueError("Failed to extract briefing text")

            self.project_type = self.detect_project_type(briefing_text)
            self.logger.info(f"Detected project type: {self.project_type}")
            
            # Análisis de requisitos y generación de resultados
            tier_requirements = self.extract_tier_requirements(briefing_text)
            
            if not tier_requirements:
                raise ValueError("Failed to extract tier requirements")
                
            analysis = self._generate_tier_analysis(
                tier_requirements=tier_requirements,
                repo_docs=repo_docs,
                repo_stats=repo_stats
            )

            return {
                "project_type": self.project_type,
                "repository_stats": repo_stats,
                "tier_analysis": analysis,
                "analysis_date": str(datetime.now())
            }

        except Exception as e:
            self.logger.error(f"Error in requirements analysis: {e}")
            return {
                "error": str(e),
                "analysis_date": str(datetime.now())
            }

    def extract_tier_requirements(self, briefing_text: str) -> Dict[str, List[str]]:
        """
        Extrae los requisitos por nivel del briefing
        Args:
            briefing_text: Texto del briefing
        Returns:
            Dict: Requisitos organizados por nivel
        """
        try:
            # Plantilla para la respuesta JSON esperada
            json_template = '''
    {
        "nivel_esencial": ["requisito1", "requisito2"],
        "nivel_medio": ["requisito1", "requisito2"],
        "nivel_avanzado": ["requisito1", "requisito2"],
        "nivel_experto": ["requisito1", "requisito2"]
    }
    '''
            # Prompt para la extracción de requisitos
            prompt = f"""
                Analiza este texto de briefing y extrae los requisitos para cada nivel.
                Enfócate en requisitos técnicos específicos de {self.project_type.upper()}.

                TEXTO DEL BRIEFING:
                {briefing_text}

                Extrae y categoriza todos los requisitos en estos niveles:
                
                - Nivel Esencial:
                {self.tier_descriptions["nivel_esencial"][self.project_type]}
                
                - Nivel Medio:
                {self.tier_descriptions["nivel_medio"][self.project_type]}
                
                - Nivel Avanzado:
                {self.tier_descriptions["nivel_avanzado"][self.project_type]}
                
                - Nivel Experto:
                {self.tier_descriptions["nivel_experto"][self.project_type]}

                Aspectos a evaluar:
                - Calidad del código y documentación
                - Implementación de mejores prácticas en IA/ML
                - Experimentación y evaluación de modelos
                - Manejo de datos y preprocesamiento
                - Optimización y rendimiento
                - Consideraciones éticas y de sesgo

                Formato JSON requerido:
                {json_template}

                Responde SOLO con el JSON, sin texto adicional.
                """

            messages = [
                SystemMessage(content="Eres un analista técnico especializado en proyectos de IA/ML en español."),
                HumanMessage(content=prompt)
            ]
            
            # Procesamiento de la respuesta
            response = self.llm.invoke(messages)
            
            # Limpieza y validación de la respuesta JSON
            try:
                response_text = response.content.strip()
                if not response_text.startswith('{'):
                    response_text = response_text[response_text.find('{'):]
                if not response_text.endswith('}'):
                    response_text = response_text[:response_text.rfind('}')+1]
                
                return json.loads(response_text)
            except json.JSONDecodeError as je:
                self.logger.error(f"Error parsing JSON response: {je}")
                return {}

        except Exception as e:
            self.logger.error(f"Error extracting tier requirements: {e}")
            return {}
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def _generate_tier_analysis(
        self,
        tier_requirements: Dict[str, List[str]],
        repo_docs: List[str],
        repo_stats: Dict
    ) -> Dict[str, Any]:
        """
        Genera el análisis detallado del proyecto
        Args:
            tier_requirements: Requisitos por nivel
            repo_docs: Documentos del repositorio
            repo_stats: Estadísticas del repositorio
        Returns:
            Dict: Análisis completo del proyecto
        """
        try:
            # Preparación del contenido para el análisis
            repo_content = "\n".join(repo_docs)
            
            # Prompt detallado para el análisis
            prompt = f"""
            Analiza este repositorio de {self.project_type.upper()} contra los requisitos especificados.
            Proporciona un análisis técnico detallado enfocado en calidad y completitud.

            REQUISITOS POR NIVEL:
            {json.dumps(tier_requirements, indent=2, ensure_ascii=False)}

            CONTENIDO DEL REPOSITORIO:
            {repo_content[:10000]}

            MÉTRICAS DEL REPOSITORIO:
            - Commits totales: {repo_stats['commit_count']}
            - Contribuidores: {len(repo_stats['contributors'])}
            - Lenguajes: {', '.join([f"{l['name']} ({l['percentage']}%)" for l in repo_stats['languages']])}

            Evalúa específicamente:
            1. Calidad del código y documentación
            2. Implementación de mejores prácticas en {self.project_type.upper()}
            3. Experimentación y evaluación de modelos
            4. Manejo de datos y preprocesamiento
            5. Optimización y rendimiento
            6. Consideraciones éticas y de sesgo

            Genera un JSON con este formato exacto, sin omitir ningún campo:
            {{
                "evaluacion_general": "Descripción general del análisis",
                "analisis_por_nivel": {{
                    "nivel_esencial": {{
                        "requisitos_cumplidos": ["req1", "req2"],
                        "requisitos_faltantes": ["req3", "req4"],
                        "calidad_implementacion": "Descripción de la calidad",
                        "porcentaje_completitud": 75,
                        "aspectos_destacados": ["aspecto1", "aspecto2"],
                        "areas_mejora": ["area1", "area2"]
                    }},
                    "nivel_medio": {{
                        "requisitos_cumplidos": [],
                        "requisitos_faltantes": [],
                        "calidad_implementacion": "",
                        "porcentaje_completitud": 0,
                        "aspectos_destacados": [],
                        "areas_mejora": []
                    }},
                    "nivel_avanzado": {{
                        "requisitos_cumplidos": [],
                        "requisitos_faltantes": [],
                        "calidad_implementacion": "",
                        "porcentaje_completitud": 0,
                        "aspectos_destacados": [],
                        "areas_mejora": []
                    }},
                    "nivel_experto": {{
                        "requisitos_cumplidos": [],
                        "requisitos_faltantes": [],
                        "calidad_implementacion": "",
                        "porcentaje_completitud": 0,
                        "aspectos_destacados": [],
                        "areas_mejora": []
                    }}
                }},
                "analisis_tecnico": {{
                    "calidad_codigo": "Descripción de la calidad del código",
                    "mejores_practicas": "Descripción de las mejores prácticas",
                    "experimentacion": "Descripción de la experimentación",
                    "manejo_datos": "Descripción del manejo de datos",
                    "optimizacion": "Descripción de la optimización",
                    "etica_sesgos": "Descripción de ética y sesgos"
                }},
                "recomendaciones": ["recomendacion1", "recomendacion2"],
                "puntuacion_madurez": 65
            }}
            """

            messages = [
                SystemMessage(content=f"Eres un analista técnico especializado en proyectos de {self.project_type.upper()} en español."),
                HumanMessage(content=prompt)
            ]
            
            # Procesamiento de la respuesta
            response = self.llm.invoke(messages)
            
            # Limpieza y validación de la respuesta JSON
            try:
                response_text = response.content.strip()
                if not response_text.startswith('{'):
                    response_text = response_text[response_text.find('{'):]
                if not response_text.endswith('}'):
                    response_text = response_text[:response_text.rfind('}')+1]
                
                analysis_result = json.loads(response_text)
                
                # Validación de campos requeridos
                required_fields = ['evaluacion_general', 'analisis_por_nivel', 'analisis_tecnico', 
                                 'recomendaciones', 'puntuacion_madurez']
                for field in required_fields:
                    if field not in analysis_result:
                        raise ValueError(f"Missing required field: {field}")
                
                return analysis_result

            except json.JSONDecodeError as je:
                self.logger.error(f"Error parsing JSON response: {je}")
                raise ValueError("Invalid JSON response from LLM")

        except Exception as e:
            self.logger.error(f"Error generating tier analysis: {e}")
            # Retorna una estructura de error predeterminada
            return {
                "evaluacion_general": "Error al generar el análisis.",
                "analisis_por_nivel": {
                    "nivel_esencial": {
                        "requisitos_cumplidos": [],
                        "requisitos_faltantes": [],
                        "calidad_implementacion": "Error en análisis",
                        "porcentaje_completitud": 0,
                        "aspectos_destacados": [],
                        "areas_mejora": []
                    },
                    "nivel_medio": {
                        "requisitos_cumplidos": [],
                        "requisitos_faltantes": [],
                        "calidad_implementacion": "Error en análisis",
                        "porcentaje_completitud": 0,
                        "aspectos_destacados": [],
                        "areas_mejora": []
                    },
                    "nivel_avanzado": {
                        "requisitos_cumplidos": [],
                        "requisitos_faltantes": [],
                        "calidad_implementacion": "Error en análisis",
                        "porcentaje_completitud": 0,
                        "aspectos_destacados": [],
                        "areas_mejora": []
                    },
                    "nivel_experto": {
                        "requisitos_cumplidos": [],
                        "requisitos_faltantes": [],
                        "calidad_implementacion": "Error en análisis",
                        "porcentaje_completitud": 0,
                        "aspectos_destacados": [],
                        "areas_mejora": []
                    }
                },
                "analisis_tecnico": {
                    "calidad_codigo": "Error en análisis",
                    "mejores_practicas": "Error en análisis",
                    "experimentacion": "Error en análisis",
                    "manejo_datos": "Error en análisis",
                    "optimizacion": "Error en análisis",
                    "etica_sesgos": "Error en análisis"
                },
                "recomendaciones": ["Error al generar recomendaciones"],
                "puntuacion_madurez": 0
            }