import os
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib import messages
from django.shortcuts import render
from reportlab.pdfgen import canvas
from dotenv import load_dotenv
import sys
import os
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
from RAG_analyzer import GitHubRAGAnalyzer
from django.http import FileResponse
import logging
import shutil

load_dotenv()

def home(request):
    """Render home page"""
    return render(request, 'home.html')

def generate_pdf_report(analysis_results, briefing_name):
    """Generate a detailed PDF report of the analysis results"""
    try:
        clean_name = briefing_name.lower().replace('.pdf', '')
        pdf_name = f"Informe_Analisis_{clean_name}.pdf"
        pdf_path = os.path.join("static/reports", pdf_name)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        c = canvas.Canvas(pdf_path)
        
        # Title
        c.setFont("Helvetica", 16)
        c.drawString(100, 800, "Informe de Análisis por Niveles")
        
        # Project Type
        c.setFont("Helvetica", 14)
        project_type_map = {
            'ml': 'Machine Learning',
            'nlp': 'Procesamiento de Lenguaje Natural',
            'genai': 'IA Generativa'
        }
        c.drawString(100, 770, f"Tipo de Proyecto: {project_type_map.get(analysis_results['project_type'], 'N/A')}")
        
        # Repository Statistics
        repo_stats = analysis_results['repository_stats']
        y = 740
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "1. Estadísticas del Repositorio")
        c.setFont("Helvetica", 12)
        y -= 20
        
        # Basic Stats and Languages
        c.drawString(120, y, f"Total Commits: {repo_stats['commit_count']}")
        y -= 20
        c.drawString(120, y, f"Lenguajes: {', '.join([f'{l['name']} ({l['percentage']}%)' for l in repo_stats['languages']])}")
        y -= 40

        # Tier Analysis
        tier_analysis = analysis_results['tier_analysis']
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "2. Análisis por Niveles")
        y -= 30

        for nivel in ['nivel_esencial', 'nivel_medio', 'nivel_avanzado', 'nivel_experto']:
            if y < 100:  # New page if needed
                c.showPage()
                y = 750
            
            nivel_data = tier_analysis['analisis_por_nivel'][nivel]
            c.setFont("Helvetica", 13)
            c.drawString(110, y, f"{nivel.replace('_', ' ').title()}")
            c.setFont("Helvetica", 12)
            y -= 20
            
            c.drawString(120, y, f"Completitud: {nivel_data['porcentaje_completitud']}%")
            y -= 20
            
            # Requirements met/unmet
            if nivel_data['requisitos_cumplidos']:
                c.drawString(120, y, "Requisitos Cumplidos:")
                y -= 20
                for req in nivel_data['requisitos_cumplidos']:
                    c.drawString(130, y, f"✓ {req[:80]}")
                    y -= 15
            
            if nivel_data['requisitos_faltantes']:
                c.drawString(120, y, "Requisitos Faltantes:")
                y -= 20
                for req in nivel_data['requisitos_faltantes']:
                    c.drawString(130, y, f"✗ {req[:80]}")
                    y -= 15
            
            y -= 20

        # Technical Analysis
        if y < 200:
            c.showPage()
            y = 750
            
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "3. Análisis Técnico")
        y -= 30
        c.setFont("Helvetica", 12)
        
        tech_analysis = tier_analysis['analisis_tecnico']
        for key, value in tech_analysis.items():
            c.drawString(120, y, f"{key.replace('_', ' ').title()}: {value[:80]}")
            y -= 20

        # Recommendations
        if y < 200:
            c.showPage()
            y = 750
            
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "4. Recomendaciones")
        y -= 30
        c.setFont("Helvetica", 12)
        
        for rec in tier_analysis['recomendaciones']:
            c.drawString(120, y, f"• {rec[:80]}")
            y -= 20

        # Maturity Score
        c.setFont("Helvetica", 14)
        c.drawString(100, y-30, f"Puntuación de Madurez: {tier_analysis['puntuacion_madurez']}/100")

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
        temp_files = []  # Track files to clean up

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
                temp_files.append(briefing_path)
                
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

                # Add cloned repo to cleanup list if it exists
                cloned_repo_path = os.path.join(root_dir, "cloned_repo")
                if os.path.exists(cloned_repo_path):
                    temp_files.append(cloned_repo_path)

                try:
                    response = None
                    if request.POST.get('download_pdf'):
                        response = FileResponse(
                            open(pdf_path, 'rb'),
                            as_attachment=True,
                            filename=os.path.basename(pdf_path)
                        )
                    
                    # Clean up temporary files
                    for file_path in temp_files:
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path, ignore_errors=True)
                        elif os.path.isfile(file_path):
                            os.remove(file_path)
                    
                    if response:
                        return response

                    return render(request, "analysis.html", {
                        "project_type": analysis_results["project_type"],
                        "repo_data": analysis_results["repository_stats"],
                        "tier_analysis": analysis_results["tier_analysis"],
                        "analysis_date": analysis_results["analysis_date"],
                        "pdf_path": f"static/reports/{os.path.basename(pdf_path)}",
                        "analysis_available": bool(analysis_results.get("tier_analysis"))
                    })

                except Exception as e:
                    logging.error(f"Error serving PDF or cleaning up: {e}")
                    messages.error(request, "Error downloading PDF file")
            else:
                messages.error(request, "Please provide a briefing file")
                
        except Exception as e:
            messages.error(request, f"Error analyzing repository: {str(e)}")
            # Clean up in case of error
            for file_path in temp_files:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path, ignore_errors=True)
                elif os.path.isfile(file_path):
                    os.remove(file_path)

    return render(request, "analysis.html", {"analysis_available": False})