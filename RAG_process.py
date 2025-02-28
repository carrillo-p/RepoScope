from typing import List, Dict, Any, Optional
import os
import logging
import json
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader, DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.document import Document

class RepoRAGProcessor:
    def __init__(self, embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the RAG processor with a specified embedding model"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize embeddings
        self.logger.info(f"Loading embedding model: {embedding_model_name}")
        try:
            model_kwargs = {'device': 'cpu'}
            encode_kwargs = {'normalize_embeddings': True, 'batch_size': 32}
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise
            
        # Configure text splitter for code and documentation
        self.code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,
            chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\n\n", "\n", " ", ""]
        )
        
        # Configure text splitter for briefing documents
        self.doc_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
        )
        
        self.vector_store = None
        
    def _filter_relevant_files(self, repo_path: str) -> List[str]:
        """Filter out non-relevant files like binaries, images, etc."""
        self.logger.info(f"Starting to filter relevant files from {repo_path}")
        relevant_extensions = [
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.html', '.css',
            '.md', '.rst', '.txt', '.json', '.yml', '.yaml', '.ipynb'
        ]
        relevant_files = []

        MAX_FILE_SIZE = 5 * 1024 * 1024
        
        file_count = 0
        for root, _, files in os.walk(repo_path):
            # Skip common directories to ignore
            if any(ignore_dir in root for ignore_dir in [
                '.git', 'node_modules', '__pycache__', 'venv', 
                'dist', 'build', 'out', '.next', '.sass-cache'
            ]):
                continue
                
            for file in files:
                file_count += 1
                if file_count % 100 == 0:
                    self.logger.info(f"Scanned {file_count} files so far...")
                    
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                
                if ext.lower() in relevant_extensions:
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > MAX_FILE_SIZE:
                            self.logger.info(f"Skipping large file {file_path} ({file_size/1024/1024:.1f}MB)")
                            continue
                        relevant_files.append(file_path)
                    except Exception:
                        continue
        
        self.logger.info(f"Found {len(relevant_files)} relevant files out of {file_count} total files in repository")
        return relevant_files
    
    def _filter_files_by_extension(self, repo_path: str, extensions: List[str]) -> List[str]:
        """Filter files by extension"""
        result_files = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                if ext.lower() in extensions:
                    result_files.append(file_path)
        return result_files

    def _detect_technologies(self, repo_path: str) -> Dict[str, List[str]]:
        """Detect technologies used in the repository by analyzing dependency files and imports"""
        technologies = {
            "languages": [],
            "frameworks": [],
            "libraries": [],
            "tools": []
        }
        
        # Check for common dependency files
        dependency_files = {
            "requirements.txt": "python",
            "package.json": "javascript",
            "pom.xml": "java",
            "Gemfile": "ruby",
            "build.gradle": "java",
            "go.mod": "go",
            "Cargo.toml": "rust"
        }
        
        for root, _, files in os.walk(repo_path):
            for file in files:
                # Check dependency files
                if file in dependency_files:
                    file_path = os.path.join(root, file)
                    tech_type = dependency_files[file]
                    technologies["languages"].append(tech_type)
                    
                    # Parse specific dependency files
                    if file == "requirements.txt":
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                for line in f:
                                    if line.strip() and not line.startswith('#'):
                                        lib = line.split('==')[0].split('>=')[0].strip()
                                        if lib:
                                            technologies["libraries"].append(lib)
                        except Exception as e:
                            self.logger.warning(f"Error parsing requirements.txt: {e}")
                    
                    elif file == "package.json":
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                data = json.load(f)
                                # Add dependencies
                                deps = data.get('dependencies', {})
                                dev_deps = data.get('devDependencies', {})
                                all_deps = list(deps.keys()) + list(dev_deps.keys())
                                technologies["libraries"].extend(all_deps)
                                # Check for popular frameworks
                                if 'react' in deps or 'react-dom' in deps:
                                    technologies["frameworks"].append("React")
                                if 'vue' in deps:
                                    technologies["frameworks"].append("Vue.js")
                                if 'angular' in deps or '@angular/core' in deps:
                                    technologies["frameworks"].append("Angular")
                        except Exception as e:
                            self.logger.warning(f"Error parsing package.json: {e}")

        # Process Python imports
        python_files = self._filter_files_by_extension(repo_path, ['.py'])
        framework_imports = {
            'flask': 'Flask',
            'django': 'Django',
            'fastapi': 'FastAPI',
            'tensorflow': 'TensorFlow',
            'torch': 'PyTorch',
            'sklearn': 'scikit-learn',
            'pandas': 'Pandas',
            'numpy': 'NumPy'
        }
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for import_name, framework_name in framework_imports.items():
                        if f"import {import_name}" in content or f"from {import_name}" in content:
                            if framework_name in ['TensorFlow', 'PyTorch', 'scikit-learn']:
                                technologies["frameworks"].append(framework_name)
                            else:
                                technologies["libraries"].append(framework_name)
            except Exception:
                continue

        for key in technologies:
            technologies[key] = sorted(list(set(technologies[key])))
                
        return technologies
        
    def process_repository(self, repo_path: str) -> bool:
        """Process repository files and create vectors with better error handling"""
        try:
            # Filter relevant files
            self.logger.info("Step 1: Filtering relevant files...")
            relevant_files = self._filter_relevant_files(repo_path)
            
            if not relevant_files:
                self.logger.error("No relevant files found in repository")
                return False
                
            # Limit files for large repositories
            MAX_FILES = 200
            if len(relevant_files) > MAX_FILES:
                self.logger.warning(f"Repository has {len(relevant_files)} files. Limiting to {MAX_FILES} for processing.")
                # Prioritize README and key files first
                priority_files = [f for f in relevant_files if 
                                os.path.basename(f).lower() == 'readme.md' or
                                'main' in os.path.basename(f).lower() or 
                                'index' in os.path.basename(f).lower()]
                other_files = [f for f in relevant_files if f not in priority_files]
                relevant_files = priority_files + other_files[:MAX_FILES-len(priority_files)]
            
            self.logger.info("Step 2: Detecting technologies...")
            try:
                technologies = self._detect_technologies(repo_path)
                self.technologies = technologies
                tech_summary = json.dumps(technologies, indent=2)
                self.logger.info(f"Detected technologies: {tech_summary}")
            except Exception as tech_err:
                self.logger.error(f"Error detecting technologies: {tech_err}")
                self.technologies = {"languages": [], "frameworks": [], "libraries": [], "tools": []}
                tech_summary = "{}"
            
            # Create a technology summary document
            tech_doc = Document(
                page_content=f"Repository Technologies:\n{tech_summary}",
                metadata={"source": "technology_analysis", "type": "metadata"}
            )
            
            # Process each file with careful memory management
            self.logger.info("Step 3: Processing files into document chunks...")
            documents = [tech_doc]
            total_files = len(relevant_files)
        
            # Process files in smaller batches to avoid memory issues
            batch_size = 20
            for batch_idx in range(0, total_files, batch_size):
                batch_end = min(batch_idx + batch_size, total_files)
                self.logger.info(f"Processing file batch {batch_idx+1}-{batch_end} of {total_files}...")
                
                for idx in range(batch_idx, batch_end):
                    file_path = relevant_files[idx]
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # Limit content size for very large files
                            MAX_CONTENT_SIZE = 50000  # ~50KB limit
                            if len(content) > MAX_CONTENT_SIZE:
                                self.logger.info(f"Truncating large file: {os.path.basename(file_path)}")
                                content = content[:MAX_CONTENT_SIZE] + "\n...[content truncated]..."
                                
                            relative_path = os.path.relpath(file_path, repo_path)
                            
                            # Create chunks
                            file_docs = self.code_splitter.create_documents(
                                texts=[content],
                                metadatas=[{"source": relative_path, "type": "code"}]
                            )
                            documents.extend(file_docs)
                    except Exception as e:
                        self.logger.warning(f"Failed to process file {file_path}: {e}")
            
            self.logger.info(f"Successfully processed {len(documents)-1} files into {len(documents)} total chunks")
            
            if len(documents) <= 1:
                self.logger.error("No documents processed from repository")
                return False
                
            # Create vector store in smaller batches
            try:
                self.logger.info("Step 4: Creating vector store from documents...")
                # Start with just the tech document to establish the vector store
                self.vector_store = FAISS.from_documents(
                    [documents[0]], 
                    self.embeddings,
                    distance_strategy='cosine'
                )
                
                # Add remaining documents in small batches
                remaining_docs = documents[1:]
                batch_size = 50  # Smaller batches for vector creation
                total_batches = (len(remaining_docs) + batch_size - 1) // batch_size
                
                for i in range(0, len(remaining_docs), batch_size):
                    batch_end = min(i + batch_size, len(remaining_docs))
                    current_batch = i // batch_size + 1
                    self.logger.info(f"Adding vector batch {current_batch}/{total_batches} ({i+1}-{batch_end} of {len(remaining_docs)})")
                    batch_docs = remaining_docs[i:batch_end]
                    self.vector_store.add_documents(batch_docs)
                
                self.logger.info(f"Repository processing complete with {len(documents)} chunks")
                return True
                
            except Exception as vector_error:
                self.logger.error(f"Error creating vector store: {vector_error}")
                # Fallback to minimal document set (just metadata)
                try:
                    self.logger.info("Attempting recovery with minimal document set...")
                    self.vector_store = FAISS.from_documents(
                        [documents[0]], 
                        self.embeddings,
                        distance_strategy='cosine'
                    )
                    self.logger.info("Recovery successful with metadata only")
                    return True
                except Exception as fallback_error:
                    self.logger.error(f"Fallback attempt also failed: {fallback_error}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Failed to process repository: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def process_briefing(self, briefing_path: str) -> bool:
        """Process briefing document and add to vector store"""
        try:
            # Load PDF
            loader = PyPDFLoader(briefing_path)
            briefing_docs = loader.load()
            
            # Split into chunks
            briefing_chunks = self.doc_splitter.split_documents(briefing_docs)
            
            # Update metadata
            for doc in briefing_chunks:
                doc.metadata["type"] = "briefing"
            
            self.logger.info(f"Briefing processed with {len(briefing_chunks)} chunks")
            
            # Add to existing store or create new one
            if self.vector_store:
                self.vector_store.add_documents(briefing_chunks)
            else:
                self.vector_store = FAISS.from_documents(briefing_chunks, self.embeddings)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process briefing: {e}")
            return False
            
    def retrieve_relevant_content(self, query: str, k: int = 8) -> List[Document]:
        """Retrieve the most relevant content for a given query"""
        if not self.vector_store:
            self.logger.error("Vector store not initialized")
            return []
            
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            return docs
        except Exception as e:
            self.logger.error(f"Failed to retrieve content: {e}")
            return []

    def get_formatted_context(self, query: str, k: int = 8) -> str:
        """Get formatted context string from relevant documents"""
        docs = self.retrieve_relevant_content(query, k)
        context_parts = []
        
        for doc in docs:
            source = doc.metadata.get("source", "unknown")
            doc_type = doc.metadata.get("type", "unknown")
            
            if doc_type == "code":
                context_parts.append(f"--- FROM CODE FILE: {source} ---\n{doc.page_content}\n")
            else:
                context_parts.append(f"--- FROM BRIEFING ---\n{doc.page_content}\n")
                
        return "\n".join(context_parts)