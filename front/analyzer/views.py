import requests
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import fitz  # PyMuPDF
from github import Github
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from django.http import FileResponse
from django.contrib import messages
from dotenv import load_dotenv
from repo_cloner import clone_repo   
from stats import analyze_commits, check_compliance_with_briefing, extract_text_from_pdf, extract_text_from_repo

load_dotenv()
GITHUB_API_URL = "https://api.github.com/repos"
TOKEN = os.getenv("GITHUB_TOKEN")

g = Github(TOKEN)

def home(request):
    return render(request, 'home.html')

def fetch_github_data(repo_url):
    """Fetch commit, contributor, language, and branch data from GitHub API."""
    try:
        repo_name = repo_url.split("github.com/")[-1].strip("/")

        if "tree" in repo_name:
                repo_name = repo_name.split("/tree/")[0]

        repo = g.get_repo(repo_name)
        branches = list(repo.get_branches())

        commit_count = 0
        contributors_data = {}

        for branch in branches:
            commits = repo.get_commits(sha=branch.name)
            branch_commits = list(commits)
            commit_count += len(branch_commits)

            for commit in branch_commits:
                    author = commit.author.login if commit.author else "Unknown"
                    contributors_data[author] = contributors_data.get(author, 0) + 1
        
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
            print(f"Error in fetch_github_data: {str(e)}")
            return {
                "branches": [],
                "commit_count": 0,
                "contributors": {},
                "languages": []
            } 
        
def analyze_repository(repo_url, briefing_file=None):
    """Clone and analyze a GitHub repository."""
    repo_path = clone_repo(repo_url)

    if not repo_path:
        return {}, {}, "", None

    # Extract repository content
    repo_docs = extract_text_from_repo(repo_path)

    # Extract briefing content if provided
    briefing_text = None
    if briefing_file:
        briefing_text = extract_text_from_pdf(briefing_file)

    # Analyze commits
    commit_stats = analyze_commits(repo_path)

    # Compare repository with briefing (if available)
    compliance_results = check_compliance_with_briefing(repo_docs, briefing_text) if briefing_text else []
    if not compliance_results:
        print("No compliance results found!")

    # Generate Markdown-style compliance results
    markdown_compliance_results = "**Compliance Report**\n\n"
    for result in compliance_results:
        status = "✅ Compliant" if result["compliant"] else "❌ Non-Compliant"
        markdown_compliance_results += f"- **Section:** {result['section']}...\n"
        markdown_compliance_results += f"  - **Similarity:** {result['similarity']}%\n"
        markdown_compliance_results += f"  - **Status:** {status}\n\n"

    return compliance_results, commit_stats, markdown_compliance_results, briefing_text

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
        
        '''for level, details in compliance_results.items():
            if isinstance(details, dict):
                c.drawString(120, y, f"{level}: {details.get('Score', 'N/A')}")
                y -= 20
                for key, value in details.items():
                    if key != "Score":
                        c.drawString(140, y, f"- {key}: {value}")
                        y -= 20
            else:
                c.drawString(120, y, f"{level}: {details}")
                y -= 20'''
        for result in compliance_results:
            status = "✅ Compliant" if result["compliant"] else "❌ Non-Compliant"
            c.drawString(120, y, f"Section: {result['section'][:50]}...")  # Truncate section
            c.drawString(140, y - 20, f"Similarity: {result['similarity']}%")
            c.drawString(140, y - 40, f"Status: {status}")
            y -= 60


        c.save()
        return pdf_path
    except Exception as e:
        print(f"Error generating PDF report: {e}")
        return None

def analysis(request):
    compliance_results = {}
    repo_data = {}
    commit_analysis = {}
    markdown_compliance_results = ""
    pdf_path = None

    if request.method == "POST":
        repo_url = request.POST.get("repo_url")
        briefing_file = request.FILES.get("briefing")

        try:
            # Save PDF to a temporary path
            briefing_text = None
            if briefing_file:
                briefing_filename = default_storage.save(f"briefings/{briefing_file.name}", ContentFile(briefing_file.read()))
                briefing_path = default_storage.path(briefing_filename)
                briefing_text = extract_text_from_pdf(briefing_path)

            # Fetch GitHub API data
            repo_data = fetch_github_data(repo_url)

            # Clone and analyze repository
            compliance_results, commit_analysis, markdown_compliance_results, _ = analyze_repository(repo_url, briefing_path)

            if compliance_results and repo_data:
                # Generate PDF report if data is available
                pdf_path = generate_pdf_report(compliance_results, repo_data, commit_analysis, briefing_file.name if briefing_file else "analysis")

        except Exception as e:
            messages.error(request, f"Error analyzing repository: {str(e)}")

    return render(request, "analysis.html", {
        "compliance_results": compliance_results,
        "repo_data": repo_data,
        "commit_analysis": commit_analysis,
        "markdown_compliance_results": markdown_compliance_results,
        "pdf_path": pdf_path
    })
