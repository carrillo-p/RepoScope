from datetime import datetime
import os
from typing import List, Dict, Any
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
import json
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
import logging
from stats import extract_text_from_pdf, extract_text_from_repo

class GitHubRAGAnalyzer:
    def __init__(
        self,
        vector_store_path: str = "./vector_store",
        model_name: str = "mixtral-8x7b-32768",  # Modelo por defecto en Groq
        api_key: str = None
    ):
        """
        Inicializa el analizador RAG para repositorios de GitHub usando Groq.
        
        Args:
            vector_store_path: Ruta donde se almacenará la base de datos vectorial
            model_name: Nombre del modelo en Groq
            api_key: API key de Groq (opcional si está en variables de entorno)
        """
        load_dotenv()  # Cargar variables de entorno
        self.vector_store_path = vector_store_path
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Se requiere API key de Groq")
        
        self.setup_logging()
        self.initialize_components()

    def setup_logging(self):
        """Configura el sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def initialize_components(self):
        """Inicializa los componentes necesarios para RAG"""
        # Usar HuggingFace para embeddings 
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Configurar Groq como LLM
        self.llm = ChatGroq(
            api_key=self.api_key,
            model_name=self.model_name
        )

        # Configurar el divisor de texto
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

    def create_qa_chain(self) -> RetrievalQA:
        """
        Crea una cadena de preguntas y respuestas usando el vector store.
        
        Returns:
            Cadena RetrievalQA configurada
        """
        # Cargar vector store existente
        vector_store = Chroma(
            persist_directory=self.vector_store_path,
            embedding_function=self.embeddings
        )
        
        # Crear y retornar la cadena QA
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever()
        )

    def process_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Procesa un repositorio de GitHub y devuelve los documentos procesados.
        
        Args:
            repo_path: Ruta al repositorio clonado
            
        Returns:
            Dict con los documentos procesados y la fecha de análisis
        """
        try:
            # Procesar archivos
            documents = self._process_files(repo_path)
            
            # Crear vector store si Andrea lo ve necesario en su parte del código
            vector_store = Chroma.from_documents(
                documents,
                self.embeddings,
                persist_directory=self.vector_store_path
            )
            
            return {
                "documentos_procesados": documents,
                "fecha_análisis": str(datetime.now())
            }
            
        except Exception as e:
            self.logger.error(f"Error procesando repositorio: {str(e)}")
            raise

    def _process_files(self, repo_path: str) -> List[Any]:
        """
        Procesa todos los archivos del repositorio.
        
        Args:
            repo_path: Ruta al repositorio clonado
            
        Returns:
            Lista de documentos procesados
        """
        documents = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                if self._should_process_file(file):
                    try:
                        file_path = os.path.join(root, file)
                        loader = TextLoader(file_path)
                        documents.extend(loader.load())
                    except Exception as e:
                        self.logger.warning(f"Error procesando archivo {file}: {str(e)}")
        
        return self.text_splitter.split_documents(documents)

    def _should_process_file(self, filename: str) -> bool:
        """
        Determina si un archivo debe ser procesado basado en su extensión.
        """
        valid_extensions = {
            '.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php',
            '.rb', '.go', '.rs', '.swift', '.kt', '.ts', '.html', '.css',
            '.md', '.txt', '.json', '.yaml', '.yml'
        }
        return any(filename.endswith(ext) for ext in valid_extensions)
    
    def extract_tasks_from_briefing(self, briefing_text: str) -> Dict[str, List[str]]:
        """
        Usa Groq para extraer tareas y clasificarlas en Essential, Intermediate y Advanced.
        
        Args:
            briefing_text: Texto del briefing
        
        Returns:
            Diccionario con tareas clasificadas en niveles
        """
        system_prompt = """
        Eres un analista de proyectos de software. Dado un briefing de un proyecto, extrae
        y estructura las tareas en niveles de prioridad: "Essential", "Intermediate", "Advanced".
        
        Devuelve un JSON con la estructura:
        {
            "Essential": ["Tarea 1", "Tarea 2"],
            "Intermediate": ["Tarea 3"],
            "Advanced": ["Tarea 4"]
        }
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Briefing:\n{briefing_text}")
        ]
        
        response = self.llm(messages)
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "No se pudo procesar el briefing"}
        
    def check_compliance_with_repo(self, briefing_tasks: Dict[str, List[str]], repo_code: str) -> Dict[str, Dict[str, str]]:
        """
        Usa Groq para verificar si las tareas del briefing están implementadas en el código.
        
        Args:
            briefing_tasks: Diccionario con tareas extraídas del briefing
            repo_code: Código del repositorio a evaluar
        
        Returns:
            Un diccionario con el estado de cada tarea (Complete / Incomplete)
        """
        system_prompt = """
        Eres un experto en análisis de código. Se te proporciona una lista de tareas del briefing 
        de un proyecto y el código del repositorio. Evalúa si cada tarea está implementada y 
        responde en JSON con el estado de cada una:
        {
            "Essential": {"Tarea 1": "Complete", "Tarea 2": "Incomplete"},
            "Intermediate": {"Tarea 3": "Complete"},
            "Advanced": {"Tarea 4": "Incomplete"}
        }
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Tareas del briefing:\n{json.dumps(briefing_tasks)}"),
            HumanMessage(content=f"Código del repositorio:\n{repo_code[:4000]}")
        ]
        
        response = self.llm(messages)
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "No se pudo evaluar el cumplimiento"}
        
if __name__ == "__main__":
    briefing_pdf = "briefing.pdf"  # Ruta del briefing en PDF
    repo_path = "./repositorio"  # Ruta del código fuente

    analyzer = GitHubRAGAnalyzer()

    # 1. Extraer texto del briefing
    briefing_text = extract_text_from_pdf(briefing_pdf)
    if not briefing_text:
        print("Error: No se pudo extraer el texto del briefing.")
        exit(1)

    # 2. Extraer tareas del briefing
    briefing_tasks = analyzer.extract_tasks_from_briefing(briefing_text)
    if "error" in briefing_tasks:
        print("Error: No se pudieron extraer las tareas del briefing.")
        exit(1)

    # 3. Procesar el repositorio y extraer código
    repo_data = analyzer.process_repository(repo_path)
    if not repo_data["documentos_procesados"]:
        print("Error: No se pudo extraer el código del repositorio.")
        exit(1)
    
    repo_code = "\n".join(doc.page_content for doc in repo_data["documentos_procesados"])

    # 4. Evaluar cumplimiento
    compliance_report = analyzer.check_compliance_with_repo(briefing_tasks, repo_code)
    if "error" in compliance_report:
        print("Error: No se pudo evaluar el cumplimiento del código.")
        exit(1)

    print("Tareas extraídas:", briefing_tasks)
    print("Informe de cumplimiento:", compliance_report)


