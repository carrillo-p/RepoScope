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
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from Github_getter import GitHubAnalyzer  # Asegúrate de tener la ruta correcta

load_dotenv()

def home(request):
    """Vista para renderizar la página principal"""
    return render(request, 'home.html')

def generate_pdf_report(analysis_results, briefing_name):
    """
    Genera un informe PDF detallado de los resultados del análisis
    Args:
        analysis_results: Resultados del análisis del repositorio
        briefing_name: Nombre del archivo briefing original
    Returns:
        str: Ruta al archivo PDF generado
    """
    try:
        # Preparación del nombre y ruta del archivo PDF
        clean_name = briefing_name.lower().replace('.pdf', '')
        pdf_name = f"Informe_Analisis_{clean_name}.pdf"
        pdf_path = os.path.join("static/reports", pdf_name)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        # Inicialización del documento PDF
        c = canvas.Canvas(pdf_path)
        
        # Título del informe
        c.setFont("Helvetica", 16)
        c.drawString(100, 800, "Informe de Análisis por Niveles")
        
        # Tipo de proyecto y mapeo para visualización
        c.setFont("Helvetica", 14)
        project_type_map = {
            'ml': 'Machine Learning',
            'nlp': 'Procesamiento de Lenguaje Natural',
            'genai': 'IA Generativa'
        }
        c.drawString(100, 770, f"Tipo de Proyecto: {project_type_map.get(analysis_results['project_type'], 'N/A')}")
        
        # Estadísticas del repositorio
        repo_stats = analysis_results['repository_stats']
        y = 740  # Posición vertical inicial
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "1. Estadísticas del Repositorio")
        c.setFont("Helvetica", 12)
        y -= 20
        
        # Estadísticas básicas y lenguajes utilizados
        c.drawString(120, y, f"Total Commits: {repo_stats['commit_count']}")
        y -= 20
        c.drawString(120, y, f"Lenguajes: {', '.join([f'{l['name']} ({l['percentage']}%)' for l in repo_stats['languages']])}")
        y -= 40

        # Análisis por niveles
        tier_analysis = analysis_results['tier_analysis']
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "2. Análisis por Niveles")
        y -= 30

        # Generar sección para cada nivel de análisis
        for nivel in ['nivel_esencial', 'nivel_medio', 'nivel_avanzado', 'nivel_experto']:
            if y < 100:  # Nueva página si es necesario
                c.showPage()
                y = 750
            
            nivel_data = tier_analysis['analisis_por_nivel'][nivel]
            c.setFont("Helvetica", 13)
            c.drawString(110, y, f"{nivel.replace('_', ' ').title()}")
            c.setFont("Helvetica", 12)
            y -= 20
            
            # Porcentaje de completitud
            c.drawString(120, y, f"Completitud: {nivel_data['porcentaje_completitud']}%")
            y -= 20
            
            # Requisitos cumplidos y faltantes
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

        # Análisis técnico
        if y < 200:
            c.showPage()
            y = 750
            
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "3. Análisis Técnico")
        y -= 30
        c.setFont("Helvetica", 12)
        
        # Detalles del análisis técnico
        tech_analysis = tier_analysis['analisis_tecnico']
        for key, value in tech_analysis.items():
            c.drawString(120, y, f"{key.replace('_', ' ').title()}: {value[:80]}")
            y -= 20

        # Recomendaciones
        if y < 200:
            c.showPage()
            y = 750
            
        c.setFont("Helvetica", 14)
        c.drawString(100, y, "4. Recomendaciones")
        y -= 30
        c.setFont("Helvetica", 12)
        
        # Lista de recomendaciones
        for rec in tier_analysis['recomendaciones']:
            c.drawString(120, y, f"• {rec[:80]}")
            y -= 20

        # Puntuación final de madurez
        c.setFont("Helvetica", 14)
        c.drawString(100, y-30, f"Puntuación de Madurez: {tier_analysis['puntuacion_madurez']}/100")

        c.save()
        return pdf_path
    except Exception as e:
        logging.error(f"Error generating PDF report: {e}")
        return None

def analysis(request):
    """
    Maneja la solicitud de análisis del repositorio
    Procesa el formulario, realiza el análisis y genera el informe
    """
    if request.method == "POST":
        repo_url = request.POST.get("repo_url")
        briefing_file = request.FILES.get("briefing")
        temp_files = []

        # Validación de entrada
        if not repo_url:
            messages.error(request, "Please provide a repository URL")
            return render(request, "analysis.html")

        try:
            # Inicialización del analizador
            analyzer = GitHubRAGAnalyzer()
            
            # Procesamiento del archivo de briefing
            if briefing_file:
                # Guardar archivo de briefing
                briefing_filename = default_storage.save(
                    f"briefings/{briefing_file.name}", 
                    ContentFile(briefing_file.read())
                )
                briefing_path = default_storage.path(briefing_filename)
                temp_files.append(briefing_path)
                
                # Realizar análisis completo
                analysis_results = analyzer.analyze_requirements_completion(
                    repo_url=repo_url,
                    briefing_path=briefing_path
                )
                
                # Verificar errores en el análisis
                if "error" in analysis_results:
                    raise ValueError(analysis_results["error"])

                # Generar informe PDF
                pdf_path = generate_pdf_report(
                    analysis_results=analysis_results,
                    briefing_name=briefing_file.name
                )

                # Añadir repo clonado a la lista de limpieza
                cloned_repo_path = os.path.join(root_dir, "cloned_repo")
                if os.path.exists(cloned_repo_path):
                    temp_files.append(cloned_repo_path)

                try:
                    # Gestión de descarga del PDF
                    response = None
                    if request.POST.get('download_pdf'):
                        response = FileResponse(
                            open(pdf_path, 'rb'),
                            as_attachment=True,
                            filename=os.path.basename(pdf_path)
                        )
                    
                    # Limpieza de archivos temporales
                    for file_path in temp_files:
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path, ignore_errors=True)
                        elif os.path.isfile(file_path):
                            os.remove(file_path)
                    
                    # Retornar respuesta de descarga si es necesario
                    if response:
                        return response

                    # Renderizar template con resultados
                    return render(request, "analysis.html", {
                        "project_type": analysis_results["project_type"],
                        "repo_data": analysis_results["repository_stats"],
                        "tier_analysis": analysis_results["tier_analysis"],
                        "analysis_date": analysis_results["analysis_date"],
                        "pdf_path": f"static/reports/{os.path.basename(pdf_path)}",
                        "analysis_available": bool(analysis_results.get("tier_analysis")),
                        "commit_analysis": analysis_results["repository_stats"].get("commit_analysis", [])
                    })

                except Exception as e:
                    logging.error(f"Error serving PDF or cleaning up: {e}")
                    messages.error(request, "Error downloading PDF file")
            else:
                messages.error(request, "Please provide a briefing file")
                
        except Exception as e:
            messages.error(request, f"Error analyzing repository: {str(e)}")
            # Limpieza en caso de error
            for file_path in temp_files:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path, ignore_errors=True)
                elif os.path.isfile(file_path):
                    os.remove(file_path)

    return render(request, "analysis.html", {"analysis_available": False})

def quick_analysis(request):
    if request.method == 'POST':
        repo_url = request.POST.get('repo_url')
        
        if not repo_url:
            messages.error(request, 'Por favor, proporciona una URL válida')
            return render(request, 'quick_analysis.html')
            
        try:
            # Inicialización del analizador de GitHub
            analyzer = GitHubAnalyzer()
            repo = analyzer.github.get_repo(analyzer._extract_repo_name(repo_url))
            
            # Obtención de commits y autores de todas las ramas
            branches = repo.get_branches()
            all_commits = []
            commit_authors = []

            # Análisis de commits por rama
            for branch in branches:
                branch_commits = repo.get_commits(sha=branch.name)
                for commit in branch_commits:
                    if commit.sha not in [c.sha for c in all_commits]:
                        all_commits.append(commit)
                        author = None
                        if commit.author:
                            author = commit.author.login
                        elif commit.commit.author.email:
                            author = commit.commit.author.email
                        else:
                            author = commit.commit.author.name
                        commit_authors.append(author)

            # Verificación de commits encontrados
            if not all_commits:
                messages.warning(request, 'No se encontraron commits en este repositorio')
                return render(request, 'quick_analysis.html')
            
            # Generación de visualizaciones
            commit_data = pd.DataFrame({
                'fecha': [c.commit.author.date.date() for c in all_commits],
                'autor': commit_authors,
                'hora': [c.commit.author.date.hour for c in all_commits],
                'cantidad': 1
            })

            # Gráfica de actividad
            fig_activity = go.Figure()
            colors = px.colors.qualitative.Set1

            for idx, autor in enumerate(commit_data['autor'].unique()):
                df_autor = commit_data[commit_data['autor'] == autor]
                df_daily = df_autor.groupby('fecha')['cantidad'].sum().reset_index()
                
                fig_activity.add_trace(
                    go.Scatter(
                        x=df_daily['fecha'],
                        y=df_daily['cantidad'],
                        name=autor,
                        mode='lines+markers'
                    )
                )

            # Gráfica de distribución de autores
            df_authors = pd.DataFrame(commit_authors, columns=['autor'])
            author_counts = df_authors['autor'].value_counts()
            
            fig_authors = px.pie(
                values=author_counts.values,
                names=author_counts.index,
                title='Distribución de Commits por Desarrollador'
            )

            # Análisis de lenguajes y estadísticas
            repo_stats = analyzer.get_repo_stats(repo_url)
            languages_data = []
            
            if repo_stats and "languages" in repo_stats:
                languages_data = repo_stats['languages']

            context = {
                'graphs': {
                    'commits_activity': fig_activity.to_html(full_html=False),
                    'developer_distribution': fig_authors.to_html(full_html=False)
                },
                'languages': languages_data,
                'libraries': repo_stats.get('libraries', [])
            }

            return render(request, 'quick_analysis.html', context)
                
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return render(request, 'quick_analysis.html')
    
    return render(request, 'quick_analysis.html')