from django.shortcuts import render
import plotly.express as px
import plotly.graph_objects as go
from django.http import JsonResponse, FileResponse, Http404
import pandas as pd
from django.contrib import messages
import json
import sys
import os
import logging
from .constants import (
    QUICK_ANALYSIS_ERROR_MESSAGES, 
    VISUALIZATION_CONFIG,
    MAIN_LIBRARIES,
    ANALYSIS_SETTINGS
)
import time
import shutil
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
from github_getter import GitHubAnalyzer

logger = logging.getLogger('repo_analyzer.views')

def quick_analysis(request):
    """Vista para el análisis rápido del repositorio"""
    if request.method == 'POST':
        repo_url = request.POST.get('repo_url')
        
        if not repo_url:
            messages.error(request, QUICK_ANALYSIS_ERROR_MESSAGES['url_required'])
            return render(request, 'quick_analysis.html')
            
        try:
            # Inicialización del analizador de GitHub
            logger.info("Initializing GitHub analyzer")
            analyzer = GitHubAnalyzer()
            repo = analyzer.github.get_repo(analyzer._extract_repo_name(repo_url))
            
            # Obtención de commits y autores de todas las ramas
            branches = repo.get_branches()
            all_commits = []
            commit_authors = []

            # Análisis de commits por rama
            for branch in branches[:ANALYSIS_SETTINGS['max_branches_analyze']]:
                try:
                    branch_commits = repo.get_commits(
                        sha=branch.name, 
                        since=pd.Timestamp.now() - pd.Timedelta(days=ANALYSIS_SETTINGS['commit_analysis_days'])
                    )
                    for commit in branch_commits:
                        if commit.sha not in [c.sha for c in all_commits]:
                            # Obtener el commit completo con todos los detalles y archivos
                            detailed_commit = repo.get_commit(commit.sha)
                            
                            # Verificar que tenemos acceso a los archivos
                            if hasattr(detailed_commit, 'files'):
                                all_commits.append(detailed_commit)
                                author = (detailed_commit.author.login if detailed_commit.author 
                                         else detailed_commit.commit.author.email or detailed_commit.commit.author.name)
                                commit_authors.append(author)
                                
                                # Debug log
                                logger.info(f"""
                                Commit details:
                                SHA: {detailed_commit.sha[:7]}
                                Author: {author}
                                Files: {len(detailed_commit.files)}
                                Has patches: {any(hasattr(f, 'patch') for f in detailed_commit.files)}
                                """)
                except Exception as e:
                    logger.warning(f"Error al analizar rama {branch.name}: {e}")
                    continue

            # Verificación de commits encontrados
            if not all_commits:
                messages.warning(request, QUICK_ANALYSIS_ERROR_MESSAGES['no_commits'])
                return render(request, 'quick_analysis.html')

            # Añadir debug
            for commit in all_commits[:5]:  # Primeros 5 commits
                detailed_commit = commit.repository.get_commit(commit.sha)
                logger.info(f"""
                Commit: {commit.sha[:7]}
                Author: {commit.author.login if commit.author else 'None'}
                Stats available: {hasattr(detailed_commit, 'stats')}
                Additions: {detailed_commit.stats.additions if hasattr(detailed_commit, 'stats') else 'N/A'}
                Deletions: {detailed_commit.stats.deletions if hasattr(detailed_commit, 'stats') else 'N/A'}
                """)

            # Debug de los primeros commits
            for commit in all_commits[:3]:
                try:
                    url = commit.url
                    response = commit._requester.requestJson("GET", url)[0]
                    logger.info(f"""
                    Debug - Commit API Response:
                    URL: {url}
                    Has stats: {'stats' in response}
                    Stats: {response.get('stats', 'No stats available')}
                    """)
                except Exception as e:
                    logger.error(f"Error getting commit data: {str(e)}")

            # Crear visualizaciones y análisis
            context = create_analysis_visualizations(all_commits, commit_authors, repo, analyzer, repo_url)
            
            # Debug después de crear el contexto
            logger.info("Debug: Verificando contexto")
            logger.info(f"Graphs keys: {context['graphs'].keys()}")

            
            return render(request, 'quick_analysis.html', context)
                
        except Exception as e:
            logger.error(f"Error en análisis rápido: {e}")
            error_message = QUICK_ANALYSIS_ERROR_MESSAGES.get(
                str(e).lower().replace(' ', '_'),
                QUICK_ANALYSIS_ERROR_MESSAGES['general_error']
            )
            messages.error(request, error_message)
            return render(request, 'quick_analysis.html')
    
    return render(request, 'quick_analysis.html')

def create_analysis_visualizations(all_commits, commit_authors, repo, analyzer, repo_url):
    logger.info(f"Found {len(all_commits)} total commits")

    repo_stats = analyzer.get_repo_stats(repo_url)

    # 1. Primero crear las gráficas de actividad y distribución
    logger.info("Generating commit activity visualization")
    
    # Generación de visualización de actividad
    commit_data = pd.DataFrame({
        'fecha': [c.commit.author.date.date() for c in all_commits],
        'autor': commit_authors,
        'hora': [c.commit.author.date.hour for c in all_commits],
        'cantidad': 1
    })

    # Creación de gráfica de actividad
    fig_activity = go.Figure()
    colors = px.colors.qualitative.Set1

    # Generación de series temporales por autor
    for idx, autor in enumerate(commit_data['autor'].unique()):
        df_autor = commit_data[commit_data['autor'] == autor]
        df_daily = df_autor.groupby('fecha')['cantidad'].sum().reset_index()
        
        # Completar fechas faltantes
        fecha_min = commit_data['fecha'].min()
        fecha_max = commit_data['fecha'].max()
        todas_fechas = pd.date_range(start=fecha_min, end=fecha_max, freq='D').date
        
        df_completo = pd.DataFrame({'fecha': todas_fechas})
        df_completo = df_completo.merge(df_daily, on='fecha', how='left')
        df_completo['cantidad'] = df_completo['cantidad'].fillna(0)
        
        # Añadir serie temporal al gráfico
        fig_activity.add_trace(
            go.Scatter(
                x=df_completo['fecha'],
                y=df_completo['cantidad'],
                name=autor,
                mode='lines+markers',
                line=dict(
                    color=colors[idx % len(colors)],
                    width=2
                ),
                marker=dict(
                    size=6,
                    color=colors[idx % len(colors)]
                ),
                hovertemplate="<b>%{text}</b><br>" +
                            "Fecha: %{x}<br>" +
                            "Commits: %{y}<br>" +
                            "<extra></extra>",
                text=[autor] * len(df_completo)
            )
        )

    # Configuración del layout de la gráfica de actividad
    fig_activity.update_layout(
        title=f'Actividad de Commits por Desarrollador (Total: {len(all_commits)} commits)',
        xaxis_title="Fecha",
        yaxis_title="Número de Commits",
        height=400,
        showlegend=True,
        legend_title="Desarrolladores",
        plot_bgcolor='rgba(240,240,240,0.2)',
        xaxis=dict(
            gridcolor='rgba(128,128,128,0.2)',
            showgrid=True,
            gridwidth=1,
            type='date'
        ),
        yaxis=dict(
            gridcolor='rgba(128,128,128,0.2)',
            showgrid=True,
            gridwidth=1,
            rangemode='tozero'
        ),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.2)',
            borderwidth=1
        ),
        hovermode='x unified'
    )

    # Generación de gráfica de distribución de desarrolladores
    try:
        df_authors = pd.DataFrame(commit_authors, columns=['autor'])
        author_counts = df_authors['autor'].value_counts()
        total_commits = len(all_commits)
        author_percentages = (author_counts / total_commits * 100).round(2)
        
        fig_authors = px.pie(
            values=author_counts.values,
            names=author_counts.index,
            title=f'Distribución de Commits por Desarrollador (Total: {total_commits})',
            hover_data=[author_percentages]
        )
        
        fig_authors.update_traces(
            hovertemplate="<b>%{label}</b><br>" +
            "Commits: %{value}<br>" +
            "Porcentaje: %{customdata:.1f}%<br>"
        )
        
        fig_authors.update_traces(
            sort=True,
            direction='clockwise'
        )
        
    except Exception as e:
        fig_authors = go.Figure()
        fig_authors.add_annotation(
            text=f"Error al procesar la distribución de commits: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )

    # 3. Análisis de lenguajes
    logger.info("Analyzing repository languages")
    languages_data = []
    
    try:
        # Obtener los lenguajes del repositorio
        repo_languages = repo.get_languages()
        total_lines = sum(repo_languages.values())
        
        if repo_languages:
            logger.info(f"Found languages: {repo_languages}")
            languages_data = [
                {
                    'name': lang,
                    'percentage': round((lines / total_lines) * 100, 2),
                    'color': px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
                }
                for i, (lang, lines) in enumerate(repo_languages.items())
            ]
            # Ordenar por porcentaje de mayor a menor
            languages_data.sort(key=lambda x: x['percentage'], reverse=True)
        else:
            logger.warning("No languages detected in repository")
            
    except Exception as e:
        logger.error(f"Error analyzing repository languages: {str(e)}")
        languages_data = []

    # 4. Detección de bibliotecas
    libraries_data = []
    logger.info("Starting library detection")
    
    try:
        # Asegurarnos de tener el objeto repo correcto
        repo_name = analyzer._extract_repo_name(repo_url)
        repo = analyzer.github.get_repo(repo_name)
        logger.info(f"Successfully connected to repo: {repo.full_name}")
        
        try:
            # Intentar obtener el archivo requirements.txt
            requirements = repo.get_contents("requirements.txt")
            content = requirements.decoded_content.decode('utf-8')
            logger.info(f"Found requirements.txt with {len(content)} bytes")
            
            # Procesar cada línea
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    package = line.split('#')[0].strip()
                    package = package.split('==')[0].split('>=')[0].strip()
                    if package:
                        libraries_data.append({
                            'name': package,
                            'category': 'Python Package',
                            'source': 'requirements.txt'
                        })
            
            logger.info(f"Found {len(libraries_data)} libraries")
            
        except Exception as e:
            logger.error(f"Error reading requirements.txt: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error accessing repository: {str(e)}")
    
    # Asegurarnos de que libraries_data esté en el contexto incluso si está vacío
    context = {
        'graphs': {
            'commits_activity': fig_activity.to_html(full_html=False, include_plotlyjs=True),
            'developer_distribution': fig_authors.to_html(full_html=False, include_plotlyjs=True),
        },
        'languages': languages_data,
        'libraries': libraries_data
    }

    return context

def download_csv(request, filename):
    """Vista para descargar archivos CSV"""
    try:
        file_path = os.path.join('github_stats', filename)
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            raise Http404("El archivo no existe")
    except Exception as e:
        logger.error(f"Error al descargar el archivo {filename}: {str(e)}")
        raise Http404("Error al descargar el archivo")