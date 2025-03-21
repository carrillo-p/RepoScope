from github import Github
import os
import logging
from dotenv import load_dotenv
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns

# Crear directorio de logs si no existe
os.makedirs('logs', exist_ok=True)

# Configuración del sistema de logging con manejadores de archivo y consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Crear un logger personalizado para GitHubAnalyzer
logger = logging.getLogger('github_analyzer')
logger.setLevel(logging.INFO)

# Crear manejadores para archivo y consola
file_handler = logging.FileHandler('logs/github_analyzer.log')
console_handler = logging.StreamHandler()

# Crear formateadores y añadirlos a los manejadores
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Añadir manejadores al logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class GitHubAnalyzer:
    """
    Clase principal para analizar repositorios de GitHub.
    Proporciona funcionalidades para extraer estadísticas, clonar repositorios
    y generar visualizaciones.
    """
    
    def __init__(self):
        """
        Inicialización del analizador.
        Configura la conexión a GitHub usando el token de autenticación
        almacenado en las variables de entorno.
        """
        load_dotenv()
        self.token = os.getenv('GITHUB_TOKEN')
        self.github = Github(self.token)
        self.logger = logger
        self.logger.info("GitHub Analyzer inicializado")

    def _extract_repo_name(self, repo_url):
        """
        Extrae el nombre del repositorio desde la URL de GitHub.
        
        Args:
            repo_url (str): URL completa del repositorio
            
        Returns:
            str: Nombre del repositorio en formato 'propietario/repo'
        """
        repo_name = repo_url.split("github.com/")[-1].strip("/")
        if "tree" in repo_name:
            repo_name = repo_name.split("/tree/")[0]
        return repo_name

    def get_repo_stats(self, repo_url):
        """
        Obtiene estadísticas completas del repositorio incluyendo ramas, commits,
        contribuidores y lenguajes de programación.
        
        Args:
            repo_url (str): URL del repositorio de GitHub
            
        Returns:
            dict: Estadísticas del repositorio con información detallada
        """
        try:
            # Inicio del análisis y verificación de límites de la API
            self.logger.info(f"Starting repository analysis for: {repo_url}")
            rate_limit = self.github.get_rate_limit()
            self.logger.info(f"API Rate Limit remaining: {rate_limit.core.remaining}")

            if rate_limit.core.remaining < 1:
                self.logger.error("GitHub API rate limit exceeded")
                return {"error": "API rate limit exceeded"}
            
            # Obtener objeto del repositorio y sus ramas
            repo = self.github.get_repo(self._extract_repo_name(repo_url))
            branches = list(repo.get_branches())

            # Inicialización de contadores y estructuras de datos
            commit_count = 0
            contributors_data = {}
            commits_by_branch_author = []
            detailed_commit_data = []
            total_additions = 0
            total_deletions = 0

            processed_commits = set()

            # Análisis de commits por rama
            for branch in branches:
                commits = repo.get_commits(sha=branch.name)
                branch_commits = list(commits)
                branch_unique_commits = 0

                for commit in branch_commits:
                    if commit.sha in processed_commits:
                        continue

                    # Ignorar commits de merge
                    is_merge_commit = False
                    if len(commit.parents) > 1:
                        is_merge_commit = True

                    elif any(pattern in commit.commit.message.lower() for pattern in [
                        "merge pull request", "merge branch", "merge remote"
                    ]):
                        is_merge_commit = True

                    if is_merge_commit:
                        self.logger.debug(f"Skipping merge commit: {commit.sha[:7]} in branch {branch.name}")
                        processed_commits.add(commit.sha)  # Mark as processed so we don't reprocess
                        continue

                    processed_commits.add(commit.sha)
                    commit_count += 1
                    branch_unique_commits += 1

                    author = commit.author.login if commit.author else "Unknown"
                    contributors_data[author] = contributors_data.get(author, 0) + 1

                    additions = commit.stats.additions
                    deletions = commit.stats.deletions
                    total_additions += additions
                    total_deletions += deletions

                    # Commit message
                    message = commit.commit.message
                    # Eliminar saltos de línea y retornos para evitar problemas en CSV
                    message = message.replace("\n", " ").replace('\r', '')

                    commit_date = commit.commit.author.date.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Recolección de datos para CSV
                    commits_by_branch_author.append({
                        'Branch': branch.name,
                        'Author': author,
                        'Commits': 1,
                        'Additions': additions,
                        'Deletions': deletions,
                        'CommitSHA': commit.sha
                    })

                    # Datos detallados de cada commit
                    detailed_commit_data.append({
                        'Branch': branch.name,
                        'Author': author,
                        'CommitSHA': commit.sha,
                        'Message': message,
                        'Additions': additions,
                        'Deletions': deletions,
                        'Date': commit_date
                    })

            # Crear DataFrame y agrupar por rama y autor
            df_commits = pd.DataFrame(commits_by_branch_author)
            grouped_commits = df_commits.groupby(['Branch', 'Author']).agg({
                'Commits': 'sum',
                'Additions': 'sum',
                'Deletions': 'sum'
            }).reset_index()
            grouped_commits_list = grouped_commits.to_dict('records')

            # Guardar estadísticas en CSV
            output_dir = 'github_stats'
            os.makedirs(output_dir, exist_ok=True)
            csv_path = os.path.join(output_dir, 'commits_by_branch_author.csv')
            grouped_commits.to_csv(csv_path, index=False)
            self.logger.info(f"Commit statistics saved to {csv_path}")

            if detailed_commit_data:
                df_detailed = pd.DataFrame(detailed_commit_data)
                detailed_csv_path = os.path.join(output_dir, 'detailed_commits.csv')
                df_detailed.to_csv(detailed_csv_path, index=False)
                self.logger.info(f"Detailed commit information saved to {detailed_csv_path}")

            # Análisis de lenguajes de programación
            try:
                self.logger.info("Attempting to get languages...")
                repo = self.github.get_repo(self._extract_repo_name(repo_url))
                
                # Obtener lenguajes (retorna dict con lenguajes y bytes de código)
                languages = repo.get_languages()
                self.logger.info(f"Raw language data: {languages}")
                
                if not languages:
                    self.logger.warning(f"No languages detected for repo: {repo.full_name}")
                    # Intentar forzar una actualización de detección de lenguajes
                    try:
                        default_branch = repo.default_branch
                        self.logger.info(f"Checking default branch: {default_branch}")
                        latest_commit = repo.get_branch(default_branch).commit
                        self.logger.info(f"Latest commit: {latest_commit.sha}")
                        languages = repo.get_languages()
                    except Exception as e:
                        self.logger.error(f"Failed to force language detection: {str(e)}")
                        languages_data = []
                
                # Procesamiento de datos de lenguajes
                if languages:
                    total_bytes = sum(languages.values())
                    languages_data = [
                        {
                            "name": lang,
                            "percentage": round((size / total_bytes) * 100, 2),
                            "bytes": size
                        }
                        for lang, size in languages.items()
                    ]
                    self.logger.info(f"Successfully processed languages: {languages_data}")
                else:
                    languages_data = []
                    
            except Exception as lang_error:
                self.logger.error(f"Error in language detection: {str(lang_error)}", exc_info=True)
                languages_data = []
            
            # Detección de bibliotecas
            try:
                libraries_data = self.detect_libraries(repo)
                self.logger.info(f"Detected {len(libraries_data)} libraries in the repository")
            except Exception as lib_error:
                self.logger.error(f"Error detecting libraries: {str(lib_error)}", exc_info=True)
                libraries_data = []

            # Retornar resultados completos
            return {
                "branches": [b.name for b in branches],
                "commit_count": commit_count,
                "contributors": contributors_data,
                "languages": languages_data,
                "libraries": libraries_data,
                "commit_analysis": grouped_commits_list,
                "total_additions": total_additions,
                "total_deletions": total_deletions
            }

        except Exception as e:
            self.logger.error(f"Error in get_repo_stats: {str(e)}")
            return {
                "branches": [],
                "commit_count": 0,
                "contributors": {},
                "languages": [],
                "libraries": [],
                "total_additions": 0,
                "total_deletions": 0
            }

    def clone_repo(self, repo_url, target_dir="cloned_repo"):
        """
        Clona un repositorio de GitHub en el directorio local especificado.
        
        Args:
            repo_url (str): URL del repositorio a clonar
            target_dir (str): Directorio destino para la clonación
        
        Returns:
            str: Ruta al directorio del repositorio clonado
        """
        try:
            # Limpiar directorio existente si existe
            if os.path.exists(target_dir):
                self.logger.info(f"Eliminando directorio existente: {target_dir}")
                os.system(f"rd /s /q {target_dir}")  # Comando Windows

            # Obtener repositorio y sus contenidos
            clone_command = f"git clone {repo_url} {target_dir}"
            os.system(clone_command)

            if not os.path.exists(target_dir):
                # Fallback al método anterior si git clone falla
                repo = self.github.get_repo(self._extract_repo_name(repo_url))
                contents = repo.get_contents("")
                os.makedirs(target_dir, exist_ok=True)
            
            # Clonar archivos y directorios
                for content in contents:
                    if content.type == "dir":
                        os.makedirs(os.path.join(target_dir, content.path), exist_ok=True)
                    elif content.type == "file":
                        with open(os.path.join(target_dir, content.path), 'wb') as f:
                            f.write(content.decoded_content)

            self.logger.info(f"Clonado exitosamente {repo_url} en {target_dir}")
            return target_dir
        except Exception as e:
            self.logger.error(f"Error al clonar repositorio: {e}")
            return None
        
    def generate_visualizations(self, stats_data, output_path='figures'):
        """
        Genera y guarda visualizaciones de las estadísticas del repositorio.
        
        Args:
            stats_data (dict): Estadísticas del repositorio de get_repo_stats
            output_path (str): Directorio para guardar las visualizaciones
        """
        try:
            # Crear directorio de salida si no existe
            if not os.path.exists(output_path):
                os.makedirs(output_path)
                
            # Convertir datos a formato DataFrame
            branch_data = pd.DataFrame({
                'Branch': stats_data['branches'], 
                'Commits': [stats_data['commit_count']] * len(stats_data['branches'])
            })
            
            author_data = pd.DataFrame({
                'Author': list(stats_data['contributors'].keys()),
                'Commits': list(stats_data['contributors'].values())
            })

            # Generar visualización de commits por rama
            plt.figure(figsize=(10, 6))
            sns.barplot(data=branch_data, x='Branch', y='Commits')
            plt.title('Total Commits by Branch')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_path, 'commits_by_branch.png'))
            plt.close()

            # Generar visualización de commits por autor
            plt.figure(figsize=(10, 6))
            sns.barplot(data=author_data, x='Author', y='Commits')
            plt.title('Total Commits by Author')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_path, 'commits_by_author.png'))
            plt.close()
            
            self.logger.info(f"Visualizations saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating visualizations: {e}")

    def extract_text_from_repo(self, repo_path="cloned_repo"):
        """
        Extrae el contenido de texto de los archivos en el repositorio.
        
        Args:
            repo_path (str): Ruta al repositorio local
            
        Returns:
            list: Lista de contenidos de texto extraídos de archivos soportados
        """
        try:
            repo_docs = []
            supported_extensions = (".py", ".md", ".txt", ".js", ".html", ".css")
            
            # Recorrer todos los archivos del repositorio
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if file.endswith(supported_extensions): 
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                repo_docs.append(f.read())
                                self.logger.debug(f"Successfully read file: {file_path}")
                        except Exception as e:
                            self.logger.error(f"Error reading {file_path}: {e}")
            
            self.logger.info(f"Extracted text from {len(repo_docs)} files in {repo_path}")
            return repo_docs
            
        except Exception as e:
            self.logger.error(f"Error extracting text from repository: {e}")
            return []
    def detect_libraries(self, repo):
        """
        Detecta las bibliotecas utilizadas en el repositorio basándose en archivos
        de dependencias (requirements.txt, package.json, etc.).
        
        Args:
            repo: Objeto de repositorio de GitHub
            
        Returns:
            list: Lista de diccionarios con información de bibliotecas detectadas
        """
        libraries_data = []
        
        try:
            # Buscar requirements.txt (Python)
            try:
                requirements = repo.get_contents("requirements.txt")
                content = requirements.decoded_content.decode('utf-8')
                self.logger.info(f"Found requirements.txt with {len(content)} bytes")
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        package = line.split('#')[0].strip()
                        package = package.split('==')[0].split('>=')[0].strip()
                        if package:
                            libraries_data.append({
                                'name': package,
                                'category': 'Python',
                                'source': 'requirements.txt'
                            })
                self.logger.info(f"Found {len(libraries_data)} Python libraries in requirements.txt")
            except Exception as e:
                self.logger.debug(f"No requirements.txt found or error: {str(e)}")
            
            # Buscar package.json (JavaScript/Node.js)
            try:
                package_json = repo.get_contents("package.json")
                content = json.loads(package_json.decoded_content.decode('utf-8'))
                
                # Procesar dependencias
                if 'dependencies' in content:
                    for package, _ in content['dependencies'].items():
                        libraries_data.append({
                            'name': package,
                            'category': 'JavaScript',
                            'source': 'package.json'
                        })
            
                # Process dev dependencies
                if 'devDependencies' in content:
                    for package, _ in content['devDependencies'].items():
                        libraries_data.append({
                            'name': package,
                            'category': 'JavaScript',
                            'source': 'package.json (dev)'
                        })
            
                self.logger.info(f"Found {len(libraries_data)} JavaScript libraries in package.json")        
            except json.JSONDecodeError:
                self.logger.debug("Error parsing package.json: Invalid JSON")
            except Exception as e:
                self.logger.debug(f"No package.json found or error parsing it: {e}")
                
            # Buscar pom.xml (Maven/Java)
            try:
                pom_xml = repo.get_contents("pom.xml")
                from xml.etree import ElementTree
                
                content = pom_xml.decoded_content.decode('utf-8')
                root = ElementTree.fromstring(content)
                
                # Buscar dependencias en pom.xml
                ns = {'': 'http://maven.apache.org/POM/4.0.0'}
                dependencies = root.findall('.//dependencies/dependency', ns)
                
                for dep in dependencies:
                    group_id = dep.find('./groupId', ns)
                    artifact_id = dep.find('./artifactId', ns)
                    
                    if group_id is not None and artifact_id is not None:
                        libraries_data.append({
                            'name': f"{group_id.text}:{artifact_id.text}",
                            'category': 'Java',
                            'source': 'pom.xml'
                        })
                    
                self.logger.info(f"Found {len(libraries_data)} libraries in pom.xml")
            except Exception as e:
                self.logger.debug(f"No pom.xml found or error: {str(e)}")
            
            return libraries_data
            
        except Exception as e:
            self.logger.error(f"Error detecting libraries: {str(e)}")
            return []
