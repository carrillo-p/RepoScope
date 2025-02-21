from github import Github
import pandas as pd
import os
import fitz
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import seaborn as sns
from git import Repo
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")

g = Github(TOKEN)

def analyze_commits(repo_path):
    """Analyze commits across all branches and contributors."""
    try:
        repo = Repo(repo_path)
        data = []

        # Get all branches
        branches = repo.git.branch('-a').split('\n')
        branches = [b.strip('* ') for b in branches if 'HEAD' not in b]

        for branch in branches:
            try:
                # Get commits for this branch
                commits = list(repo.iter_commits(branch))
                for commit in commits:
                    author = commit.author.name if commit.author else "Unknown"
                    # Check if this commit hasn't been counted for this branch
                    entry = {
                        'Branch': branch.replace('remotes/origin/', ''),
                        'Author': author,
                        'Commits': 1
                    }
                    data.append(entry)
            except Exception as branch_error:
                print(f"Error processing branch {branch}: {branch_error}")
                continue

        # Convert to DataFrame and group by Branch and Author
        df = pd.DataFrame(data)
        stats = df.groupby(['Branch', 'Author'])['Commits'].sum().reset_index()
        return stats.to_dict('records')
    except Exception as e:
        print(f"Error in analyze_commits: {e}")
        return []

def save_commit_stats(stats, output_path="commit_stats.csv"):
    """Save commit statistics to a CSV file."""
    stats.to_csv(output_path, index=False)
    print(f"Commit stats saved to {output_path}")

def extract_text_from_repo(repo_path):
    """
    Extracts text content from files in a given repository path.
    Returns a list of extracted text from each file.
    """
    repo_docs = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".py", ".md", ".txt", ".js", ".html", ".css")): 
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        repo_docs.append(f.read())
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    return repo_docs

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a given PDF file.
    """
    text = ""
    try:
        doc = fitz.open(pdf_path)
        text = " ".join([page.get_text() for page in doc])
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def check_compliance_with_briefing(repo_docs, briefing_text):
    """
    Compares repository content with briefing requirements using vector embeddings.
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Convert briefing text to embeddings
    briefing_embedding = embeddings.embed_query(briefing_text)

    # Convert repository text to embeddings
    repo_embeddings = [embeddings.embed_query(doc) for doc in repo_docs]

    # Compute similarity scores
    similarities = cosine_similarity([briefing_embedding], repo_embeddings)[0]

    compliance_results = []
    threshold = 0.7  # Minimum similarity for compliance

    for idx, sim in enumerate(similarities):
        compliance_results.append({
            "section": repo_docs[idx][:100],  
            "similarity": round(sim * 100, 2),
            "compliant": sim >= threshold
        })

    return compliance_results

def generate_visualizations(stats, output_path='.'):
    """Generate and save commit visualizations."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    # Plot: Total commits by branch
    plt.figure(figsize=(10, 6))
    branch_commits = stats.groupby('Branch')['Commits'].sum()
    sns.barplot(x=branch_commits.index, y=branch_commits.values)
    plt.title('Total Commits by Branch')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_path, 'commits_by_branch.png'))
    plt.close()
    
    # Plot: Distribution of commits per author
    plt.figure(figsize=(10, 6))
    author_commits = stats.groupby('Author')['Commits'].sum()
    sns.barplot(x=author_commits.index, y=author_commits.values)
    plt.title('Total Commits by Author')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_path, 'commits_by_author.png'))
    plt.close()

# Example execution
if __name__ == "__main__":
    repo_path = "path/to/local/repo"  # Change this to the correct path
    stats = analyze_commits(repo_path)
    save_commit_stats(stats)
    generate_visualizations(stats, 'figures')