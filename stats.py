from github import Github
import pandas as pd
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import seaborn as sns
from git import Repo

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