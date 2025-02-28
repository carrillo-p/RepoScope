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
from github_getter import GitHubAnalyzer  # Asegúrate de tener la ruta correcta
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import Color
import json
from .constants import ANALYSIS_ERROR_MESSAGES, PROJECT_TYPES, ANALYSIS_CONFIG

load_dotenv()

logger = logging.getLogger(__name__)

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

        # Configuración del documento
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )

        # Estilos
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            spaceBefore=30,
            textColor=Color(0.2, 0.2, 0.2)
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            spaceBefore=20,
            textColor=Color(0.3, 0.3, 0.3)
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )
        
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=Color(0, 0, 0.5),
            spaceAfter=15)
        
        subsection_style = ParagraphStyle(
            'Subsection',
            parent=styles['Normal'],
            fontSize=10,
            textColor=Color(0.2, 0.2, 0.2),
            leftIndent=20,
            spaceAfter=10)

        # Contenido del documento
        story = []
        
        # Título del informe
        story.append(Paragraph("Informe de Análisis por Niveles", title_style))
        
        # Estadísticas del repositorio
        repo_stats = analysis_results['repository_stats']
        story.append(Paragraph("1. Estadísticas del Repositorio", heading_style))
        story.append(Paragraph(
            f"Total Commits: {repo_stats['commit_count']}", 
            normal_style
        ))
        story.append(Paragraph("Análisis Completo", heading_style))
        
        # Simplemente tomar el texto crudo y dividirlo por líneas
        raw_text = analysis_results['tier_analysis']['evaluacion_general']
        
        # Procesar cada línea del texto
        for line in raw_text.split('\n'):
            if not line.strip():
                continue
                
            # Detectar encabezados básicos por el número de #
            if line.startswith('# '):
                story.append(Paragraph(line[2:], styles['Heading1']))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], styles['Heading2']))
            elif line.startswith('### '):
                story.append(Paragraph(line[4:], styles['Heading3']))
            elif line.startswith('- ') or line.startswith('* '):
                # Bullet point
                story.append(Paragraph('• ' + line[2:], 
                    ParagraphStyle('bullet', parent=normal_style, leftIndent=20)))
            else:
                # Texto normal
                story.append(Paragraph(line, normal_style))
            
            # Añadir un pequeño espacio después de cada línea
            story.append(Spacer(1, 5))

        # Construir el documento
        doc.build(story)
        return pdf_path
        
    except Exception as e:
        logging.error(f"Error generating PDF report: {e}")
        return None
    
def parse_markdown_analysis(markdown_content):
    """Helper to structure markdown analysis for template"""
    sections = []
    current_section = {}
    
    for line in markdown_content.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections.append(current_section)
            current_section = {
                'title': line[3:].strip(),
                'content': []
            }
        elif line.startswith('### '):
            current_section['content'].append({
                'type': 'subheader',
                'text': line[4:].strip()
            })
        elif line.strip() and current_section:
            current_section['content'].append({
                'type': 'paragraph',
                'text': line.strip()
            })
    
    if current_section:
        sections.append(current_section)
    
    return sections

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
            messages.error(request, ANALYSIS_ERROR_MESSAGES['url_invalid'])
            return render(request, "analysis.html")

        if not briefing_file:
            messages.error(request, ANALYSIS_ERROR_MESSAGES['briefing_required'])
            return render(request, "analysis.html")

        try:
            analyzer = GitHubRAGAnalyzer()
            
            # Guardar archivo de briefing
            try:
                briefing_filename = default_storage.save(
                    f"briefings/{briefing_file.name}", 
                    ContentFile(briefing_file.read())
                )
                briefing_path = default_storage.path(briefing_filename)
                temp_files.append(briefing_path)
            except Exception as e:
                logger.error(f"Error al procesar el archivo briefing: {e}")
                messages.error(request, ANALYSIS_ERROR_MESSAGES['file_processing_error'])
                return render(request, "analysis.html")

            # Realizar análisis
            try:
                analysis_results = analyzer.analyze_requirements_completion(
                    repo_url=repo_url,
                    briefing_path=briefing_path
                )

                if not analysis_results or 'project_type' not in analysis_results:
                    raise ValueError(ANALYSIS_ERROR_MESSAGES['analysis_error'])

                # Generar informe PDF
                clean_name = briefing_file.name.lower().replace('.pdf', '')
                pdf_name = f"Informe_Analisis_{clean_name}.pdf"
                
                pdf_path = generate_pdf_report(
                    analysis_results=analysis_results,
                    briefing_name=briefing_file.name
                )

                if not pdf_path:
                    raise ValueError(ANALYSIS_ERROR_MESSAGES['pdf_generation_error'])

                # Añadir repo clonado a la lista de limpieza
                cloned_repo_path = os.path.join(root_dir, "cloned_repo")
                if os.path.exists(cloned_repo_path):
                    temp_files.append(cloned_repo_path)

                # Gestión de descarga del PDF
                if request.POST.get('download_pdf'):
                    if os.path.exists(pdf_path):
                        try:
                            response = FileResponse(
                                open(pdf_path, 'rb'),
                                content_type='application/pdf',
                                as_attachment=True,
                                filename=pdf_name  # Usamos el nombre formateado
                            )
                            # Limpieza antes de retornar
                            for file_path in temp_files:
                                try:
                                    if os.path.isdir(file_path):
                                        shutil.rmtree(file_path, ignore_errors=True)
                                    elif os.path.isfile(file_path):
                                        os.remove(file_path)
                                except Exception as e:
                                    logger.error(f"Error al limpiar archivo temporal {file_path}: {e}")
                            return response
                        except Exception as e:
                            logger.error(f"Error al descargar PDF: {str(e)}")
                            messages.error(request, ANALYSIS_ERROR_MESSAGES['pdf_generation_error'])
                    else:
                        logger.error("Archivo PDF no encontrado")
                        messages.error(request, ANALYSIS_ERROR_MESSAGES['pdf_generation_error'])

                # Preparar contexto para la plantilla
                context = {
                    "project_type": PROJECT_TYPES.get(
                        analysis_results["project_type"], 
                        PROJECT_TYPES['other']
                    ),
                    "repo_data": analysis_results["repository_stats"],
                    "tier_analysis": analysis_results["tier_analysis"],
                    "analysis_date": analysis_results["analysis_date"],
                    "pdf_path": f"static/reports/{os.path.basename(pdf_path)}",
                    "analysis_available": True,
                    "commit_analysis": analysis_results["repository_stats"].get("commit_analysis", []),
                    "structured_analysis": parse_markdown_analysis(
                        analysis_results["tier_analysis"]["evaluacion_general"]),
                    "pdf_filename": pdf_name  # Usamos el nombre formateado
                }

                return render(request, "analysis.html", context)

            except json.JSONDecodeError as je:
                logger.error(f"Error parsing JSON response: {je}")
                messages.error(request, ANALYSIS_ERROR_MESSAGES['api_error'])
                return render(request, "analysis.html")
            except ValueError as ve:
                logger.error(f"Error de validación: {ve}")
                messages.error(request, str(ve))
                return render(request, "analysis.html")
            except Exception as e:
                logger.error(f"Error inesperado: {str(e)}")
                messages.error(request, "Ha ocurrido un error inesperado durante el análisis")
            finally:
                # Limpieza de archivos temporales
                for file_path in temp_files:
                    try:
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path, ignore_errors=True)
                        elif os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Error al limpiar archivo temporal {file_path}: {str(e)}")

        except Exception as e:
            logger.error(f"Error en el análisis del repositorio: {str(e)}")
            messages.error(request, f"Error al analizar el repositorio: {str(e)}")
            return render(request, "analysis.html")

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