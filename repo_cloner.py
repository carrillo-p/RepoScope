import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from git import Repo, exc
from src.RAG_analyzer import GitHubRAGAnalyzer

# Load environment variables
load_dotenv()

def clone_repo(repo_url, target_dir="cloned_repo"):
    """Clone a repository with all branches"""
    try:
        # Remove existing repo if exists
        if os.path.exists(target_dir):
            print(f"Removing existing directory: {target_dir}")
            os.system(f"rm -rf {target_dir}")

        # Clone the repository (all branches)
        repo = Repo.clone_from(repo_url, target_dir)
        print(f"Cloned {repo_url} to {target_dir}")
        return target_dir
    except exc.GitCommandError as e:
        print(f"Error cloning repository: {e}")
        return None

def get_all_branches(repo_path):
    """Retrieve all branches from a cloned repository"""
    try:
        repo = Repo(repo_path)
        return [branch.name for branch in repo.branches]
    except exc.GitCommandError as e:
        print(f"Error fetching branches: {e}")
        return []
    
def process_repo_with_rag(repo_path):
    """
    Processes a cloned repo using RAG analysis.
    """
    analyzer = GitHubRAGAnalyzer()
    results = analyzer.process_repository(repo_path)
    return results