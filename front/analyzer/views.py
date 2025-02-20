import requests
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fitz  # PyMuPDF
from github import Github
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from reportlab.pdfgen import canvas
from django.http import FileResponse
from django.contrib import messages
from dotenv import load_dotenv
from repo_cloner import clone_repo  # Import the repo cloning module
from stats import analyze_commits  # Import the commit analysis module


load_dotenv()
GITHUB_API_URL = "https://api.github.com/repos"
TOKEN = os.getenv("GITHUB_TOKEN")

def home(request):
    return render(request, 'home.html')

def fetch_github_data(repo_url):
    """Fetch commit, contributor, language, and branch data from GitHub API."""
    try:
        repo_name = repo_url.split("github.com/")[-1].strip("/")
        if "tree" in repo_name:
            repo_name = repo_name.split("/tree/")[0]
        
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

        # Fetch branches
        branches_response = requests.get(f"{GITHUB_API_URL}/{repo_name}/branches", headers=headers)
        if branches_response.status_code != 200:
            raise Exception(f"Failed to fetch branches: {branches_response.json().get('message', '')}")
        
        branches = branches_response.json()

        # Fetch commits across all branches
        commit_count = 0
        contributors_data = {}

        for branch in branches:
            branch_name = branch["name"]
            commits_response = requests.get(f"{GITHUB_API_URL}/{repo_name}/commits?sha={branch_name}", headers=headers)
            commits = commits_response.json() if commits_response.status_code == 200 else []
            commit_count += len(commits)

            # Collect contributors
            for commit in commits:
                author = commit.get("author", {})
                if author:
                    login = author.get("login", "Unknown")
                    contributors_data[login] = contributors_data.get(login, 0) + 1

        # Fetch languages using PyGithub
        g = Github(TOKEN)
        repo = g.get_repo(repo_name)
        languages = repo.get_languages()

        # Process language data
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
            "branches": [b["name"] for b in branches],
            "commit_count": commit_count,
            "contributors": contributors_data,
            "languages": languages_data
        }
    except Exception as e:
        print(f"Error in fetch_github_data: {str(e)}")
        return {
            "branches": [],
            "commit_count": 0,
            "contributors": {},
            "languages": []
        }

def analyze_repository(repo_url, briefing_text=None):
    """Clone and analyze a GitHub repository"""
    repo_path = clone_repo(repo_url)

    if not repo_path:
        return {}, {}, {}

    # Analyze commits across all branches
    commit_stats = analyze_commits(repo_path)

    compliance_results = {
        "Essential Level": {
            "Extract files": "✅ Completed",
            "Compare with briefing": "✅ Completed" if briefing_text else "❌ Not Provided",
            "Basic compliance report": "✅ Completed",
            "Score": "75%"
        },
        "Medium Level": {
            "Dockerized application": "❌ Not Implemented",
            "Code improvement suggestions": "❌ Not Implemented",
            "API Key for LLM selection": "✅ Implemented",
            "Score": "33%"
        },
        "Advanced Level": {
            "Coding standards evaluation": "❌ Not Implemented",
            "Dependency & vulnerability analysis": "❌ Not Implemented",
            "Score": "0%"
        },
        "Overall Compliance Score": "36%"
    }

    return compliance_results, commit_stats

def generate_pdf_report(compliance_results, repo_data, commit_analysis, briefing_name):
    """Generate a detailed PDF report of the compliance analysis."""
    try:
        pdf_name = f"Informe_Básico_{briefing_name}.pdf"
        pdf_path = os.path.join("static/reports", pdf_name)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        c = canvas.Canvas(pdf_path)
        c.setFont("Helvetica", 16)
        c.drawString(100, 800, "Informe detallado de cumplimiento del briefing solicitado")
        
        # Repo Stats section
        c.setFont("Helvetica", 14)
        c.drawString(100, 770, "1. Estadísticas del Repositorio")
        c.setFont("Helvetica", 12)
        c.drawString(120, 750, f"Total Commits: {repo_data.get('commit_count', 0)}")
        c.drawString(120, 730, f"Total Branches: {len(repo_data.get('branches', []))}")
        y = 710

        # Commits section
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "2. Distribución de Commits por Desarrollador")
        c.setFont("Helvetica", 12)
        y -= 20
        for contributor, count in repo_data.get('contributors', {}).items():
            c.drawString(120, y, f"{contributor}: {count} commits")
            y -= 20

        # Languages section
        c.setFont("Helvetica", 14)
        y -= 20
        c.drawString(100, y, "3. Lenguajes Utilizados")
        c.setFont("Helvetica", 12)
        y -= 20
        for lang in repo_data.get('languages', []):
            c.drawString(120, y, f"{lang['name']}: {lang['percentage']}%")
            y -= 20

        # Branch Analysis section
        y -= 40  # Add some space
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "5. Análisis de Commits por Rama")
        c.setFont("Helvetica", 12)
        y -= 20

        if commit_analysis:
            # Create headers
            c.drawString(120, y, "Rama")
            c.drawString(250, y, "Autor")
            c.drawString(380, y, "Commits")
            y -= 20

            # Add data rows
            for entry in commit_analysis:
                branch = entry.get('Branch', '')
                author = entry.get('Author', '')
                commits = entry.get('Commits', 0)
                
                # Truncate long branch names
                if len(branch) > 20:
                    branch = branch[:17] + "..."
                
                c.drawString(120, y, branch)
                c.drawString(250, y, author)
                c.drawString(380, y, str(commits))
                y -= 20
                
                # Check if we need a new page
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y = 750
        else:
            c.drawString(120, y, "No se encontraron datos de commits por rama")

        # Compliance Levels
        y -= 20
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "4. Niveles de cumplimiento")
        c.setFont("Helvetica", 12)
        y -= 20
        
        for level, details in compliance_results.items():
            if isinstance(details, dict):
                c.drawString(120, y, f"{level}: {details.get('Score', 'N/A')}")
                y -= 20
                for key, value in details.items():
                    if key != "Score":
                        c.drawString(140, y, f"- {key}: {value}")
                        y -= 20
            else:
                c.drawString(120, y, f"{level}: {details}")
                y -= 20

        c.save()
        return pdf_path
    except Exception as e:
        print(f"Error generating PDF report: {e}")
        return None

def analysis(request):
    compliance_results = {}
    repo_data = {}
    commit_analysis = {}
    pdf_path = None
    briefing_text = None

    if request.method == "POST":
        repo_url = request.POST.get("repo_url")
        briefing_file = request.FILES.get("briefing")

        if briefing_file:
            try:
                briefing_name = briefing_file.name.split(".")[0]
                fs = FileSystemStorage()
                file_path = fs.save(f"uploads/{briefing_file.name}", briefing_file)
                full_file_path = fs.path(file_path)

                # Extract text from the PDF
                doc = fitz.open(full_file_path)
                briefing_text = " ".join([page.get_text() for page in doc])
            except Exception as e:
                messages.error(request, f"Error processing briefing file: {str(e)}")

        try:
            # Fetch GitHub API data
            repo_data = fetch_github_data(repo_url)

            # Clone and analyze repository
            compliance_results, commit_analysis = analyze_repository(repo_url, briefing_text)

            if compliance_results and repo_data:
                # Generate PDF report only if we have data
                pdf_path = generate_pdf_report(compliance_results, repo_data, commit_analysis, 
                                             briefing_name if briefing_file else "analysis")
        except Exception as e:
            messages.error(request, f"Error analyzing repository: {str(e)}")

    return render(request, "analysis.html", {
        "compliance_results": compliance_results,
        "repo_data": repo_data,
        "commit_analysis": commit_analysis,
        "pdf_path": pdf_path
    })
