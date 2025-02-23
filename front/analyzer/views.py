import os
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib import messages
from reportlab.pdfgen import canvas
from dotenv import load_dotenv
import sys
import os
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
from RAG_analyzer import GitHubRAGAnalyzer

load_dotenv()

def home(request):
    """Render home page"""
    return render(request, 'home.html')

def generate_pdf_report(analysis_results, briefing_name):
    """Generate a detailed PDF report of the analysis results"""
    try:
        pdf_name = f"Informe_Análisis_{briefing_name}.pdf"
        pdf_path = os.path.join("static/reports", pdf_name)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        c = canvas.Canvas(pdf_path)
        
        # Title
        c.setFont("Helvetica", 16)
        c.drawString(100, 800, "Informe detallado de cumplimiento del briefing")
        
        # Repository Statistics
        repo_stats = analysis_results['repository_stats']
        c.setFont("Helvetica", 14)
        c.drawString(100, 770, "1. Estadísticas del Repositorio")
        c.setFont("Helvetica", 12)
        y = 750
        
        # Basic Stats
        c.drawString(120, y, f"Total Commits: {repo_stats['commit_count']}")
        c.drawString(120, y-20, f"Total Branches: {len(repo_stats['branches'])}")
        y -= 50

        # Contributors Section
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "2. Distribución de Commits por Desarrollador")
        c.setFont("Helvetica", 12)
        y -= 20
        for contributor, count in repo_stats['contributors'].items():
            c.drawString(120, y, f"{contributor}: {count} commits")
            y -= 20

        # Languages Section
        y -= 20
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "3. Lenguajes Utilizados")
        c.setFont("Helvetica", 12)
        y -= 20
        for lang in repo_stats['languages']:
            c.drawString(120, y, f"{lang['name']}: {lang['percentage']}%")
            y -= 20

        # Compliance Results
        y -= 20
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "4. Análisis de Cumplimiento")
        c.setFont("Helvetica", 12)
        y -= 20
        
        for result in analysis_results['compliance_results']:
            status = "✅ Compliant" if result["compliant"] else "❌ Non-Compliant"
            c.drawString(120, y, f"Section: {result['section'][:50]}...")
            c.drawString(140, y - 20, f"Similarity: {result['similarity']}%")
            c.drawString(140, y - 40, f"Status: {status}")
            y -= 60

        # LLM Analysis
        if y < 100:  # New page if needed
            c.showPage()
            y = 750
            c.setFont("Helvetica", 14)
        
        c.drawString(100, y, "5. Análisis Detallado (LLM)")
        c.setFont("Helvetica", 12)
        y -= 20
        
        # Split LLM analysis into lines and write
        llm_analysis = analysis_results.get('llm_analysis', '').split('\n')
        for line in llm_analysis:
            if y < 50:  # New page if needed
                c.showPage()
                y = 750
                c.setFont("Helvetica", 12)
            c.drawString(120, y, line[:80])  # Limit line length
            y -= 20

        c.save()
        return pdf_path
    except Exception as e:
        logging.error(f"Error generating PDF report: {e}")
        return None

def analysis(request):
    """Handle repository analysis request"""
    if request.method == "POST":
        repo_url = request.POST.get("repo_url")
        briefing_file = request.FILES.get("briefing")

        if not repo_url:
            messages.error(request, "Please provide a repository URL")
            return render(request, "analysis.html")

        try:
            # Initialize analyzer
            analyzer = GitHubRAGAnalyzer()
            
            # Save and process briefing file
            if briefing_file:
                briefing_filename = default_storage.save(
                    f"briefings/{briefing_file.name}", 
                    ContentFile(briefing_file.read())
                )
                briefing_path = default_storage.path(briefing_filename)
                
                # Perform complete analysis
                analysis_results = analyzer.analyze_requirements_completion(
                    repo_url=repo_url,
                    briefing_path=briefing_path
                )
                
                if "error" in analysis_results:
                    raise ValueError(analysis_results["error"])

                # Generate PDF report
                pdf_path = generate_pdf_report(
                    analysis_results=analysis_results,
                    briefing_name=briefing_file.name
                )

                return render(request, "analysis.html", {
                    "repo_data": analysis_results["repository_stats"],
                    "compliance_results": analysis_results["compliance_results"],
                    "llm_analysis": analysis_results["llm_analysis"],
                    "analysis_date": analysis_results["analysis_date"],
                    "pdf_path": pdf_path
                })
            else:
                messages.error(request, "Please provide a briefing file")
                
        except Exception as e:
            messages.error(request, f"Error analyzing repository: {str(e)}")

    return render(request, "analysis.html")