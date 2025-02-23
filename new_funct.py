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
        Get repository statistics including branches, commits, contributors and languages
        
        Args:
            repo_url (str): URL of the GitHub repository
            
        Returns:
            dict: Repository statistics containing branches, commit count, contributors, and languages
        """
        try:
            repo = self.github.get_repo(self._extract_repo_name(repo_url))
            branches = list(repo.get_branches())

            # Initialize counters and data collection
            commit_count = 0
            contributors_data = {}
            commits_by_branch_author = []

            # Analyze commits by branch
            for branch in branches:
                commits = repo.get_commits(sha=branch.name)
                branch_commits = list(commits)
                commit_count += len(branch_commits)

                for commit in branch_commits:
                    author = commit.author.login if commit.author else "Unknown"
                    contributors_data[author] = contributors_data.get(author, 0) + 1
                    
                    # Collect data for CSV
                    commits_by_branch_author.append({
                        'Branch': branch.name,
                        'Author': author,
                        'Commits': 1  # Each commit counts as 1
                    })

            # Create DataFrame and group by Branch and Author
            df_commits = pd.DataFrame(commits_by_branch_author)
            grouped_commits = df_commits.groupby(['Branch', 'Author'])['Commits'].sum().reset_index()

            # Save to CSV with timestamp
            output_dir = 'github_stats'
            os.makedirs(output_dir, exist_ok=True)
            csv_path = os.path.join(output_dir, 'commits_by_branch_author.csv')
            grouped_commits.to_csv(csv_path, index=False)
            self.logger.info(f"Commit statistics saved to {csv_path}")

            # Analyze languages
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

    def extract_text_from_repo(self, repo_path="cloned_repo"):
        """
        Extracts text content from files in a given repository path.
        
        Args:
            repo_path (str): Path to the local repository
            
        Returns:
            list: List of extracted text content from supported file types
        """
        try:
            repo_docs = []
            supported_extensions = (".py", ".md", ".txt", ".js", ".html", ".css")
            
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
