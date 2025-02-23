from github import Github
import os
import logging
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('github_analyzer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class GitHubAnalyzer:
    def __init__(self):
        """Inicializar analizador de GitHub con token"""
        load_dotenv()
        self.token = os.getenv('GITHUB_TOKEN')
        self.github = Github(self.token)
        self.logger = logging.getLogger(__name__)

    def _extract_repo_name(self, repo_url):
        """
        Extraer nombre del repositorio desde la URL de GitHub
        
        Args:
            repo_url (str): URL del repositorio de GitHub
            
        Returns:
            str: Nombre del repositorio en formato 'propietario/repo'
        """
        repo_name = repo_url.split("github.com/")[-1].strip("/")
        if "tree" in repo_name:
            repo_name = repo_name.split("/tree/")[0]
        return repo_name

    def get_repo_stats(self, repo_url):
        """
        Obtener estadísticas del repositorio incluyendo ramas, commits, contribuidores y lenguajes
        
        Args:
            repo_url (str): URL del repositorio de GitHub
            
        Returns:
            dict: Estadísticas del repositorio conteniendo ramas, cantidad de commits, contribuidores y lenguajes
        """
        try:
            repo = self.github.get_repo(self._extract_repo_name(repo_url))
            branches = list(repo.get_branches())

            # Inicializar contadores
            commit_count = 0
            contributors_data = {}

            # Analizar commits por rama
            for branch in branches:
                commits = repo.get_commits(sha=branch.name)
                branch_commits = list(commits)
                commit_count += len(branch_commits)

                for commit in branch_commits:
                    author = commit.author.login if commit.author else "Unknown"
                    contributors_data[author] = contributors_data.get(author, 0) + 1

            # Analizar lenguajes del repositorio
            languages = repo.get_languages()
            total_bytes = sum(languages.values()) if languages else 0
            languages_data = []

            if total_bytes > 0:
                languages_data = [
                    {
                        "name": lang,
                        "percentage": round((size / total_bytes) * 100, 2)
                    }
                    for lang, size in languages.items()
                ]

            return {
                "branches": [b.name for b in branches],
                "commit_count": commit_count,
                "contributors": contributors_data,
                "languages": languages_data
            }

        except Exception as e:
            self.logger.error(f"Error in get_repo_stats: {str(e)}")
            return {
                "branches": [],
                "commit_count": 0,
                "contributors": {},
                "languages": []
            }

    def clone_repo(self, repo_url, target_dir="cloned_repo"):
        """
        Clonar un repositorio de GitHub
        
        Args:
            repo_url (str): URL del repositorio de GitHub
            target_dir (str): Directorio destino para clonar el repositorio
        
        Returns:
            str: Ruta al directorio del repositorio clonado
        """
        try:
            if os.path.exists(target_dir):
                self.logger.info(f"Eliminando directorio existente: {target_dir}")
                os.system(f"rd /s /q {target_dir}")  # Comando específico de Windows

            repo = self.github.get_repo(self._extract_repo_name(repo_url))
            
            # Obtener contenidos de la rama principal y clonar
            contents = repo.get_contents("")
            os.makedirs(target_dir, exist_ok=True)
            
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
        Generate and save visualizations of repository statistics
        
        Args:
            stats_data (dict): Repository statistics from get_repo_stats
            output_path (str): Directory to save visualization files
        """
        try:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
                
            # Convert data to DataFrame format
            branch_data = pd.DataFrame({'Branch': stats_data['branches'], 
                                        'Commits': [stats_data['commit_count']] * len(stats_data['branches'])})
            
            author_data = pd.DataFrame({'Author': list(stats_data['contributors'].keys()),
                                        'Commits': list(stats_data['contributors'].values())})

            # Generate branch visualization
            plt.figure(figsize=(10, 6))
            sns.barplot(data=branch_data, x='Branch', y='Commits')
            plt.title('Total Commits by Branch')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_path, 'commits_by_branch.png'))
            plt.close()

            # Generate author visualization 
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
