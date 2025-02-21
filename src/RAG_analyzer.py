from datetime import datetime
import os
from typing import List, Dict, Any
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import logging

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