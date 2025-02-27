from github import Github
import os
import logging
from dotenv import load_dotenv
import pandas as pd
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

                    processed_commits.add(commit.sha)
                    commit_count += 1
                    branch_unique_commits += 1

                    author = commit.author.login if commit.author else "Unknown"
                    contributors_data[author] = contributors_data.get(author, 0) + 1

                    additions = commit.stats.additions
                    deletions = commit.stats.deletions
                    total_additions += additions
                    total_deletions += deletions
                    
                    # Recolección de datos para CSV
                    commits_by_branch_author.append({
                        'Branch': branch.name,
                        'Author': author,
                        'Commits': 1,
                        'Additions': additions,
                        'Deletions': deletions,
                        'CommitSHA': commit.sha
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

            # Retornar resultados completos
            return {
                "branches": [b.name for b in branches],
                "commit_count": commit_count,
                "contributors": contributors_data,
                "languages": languages_data,
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