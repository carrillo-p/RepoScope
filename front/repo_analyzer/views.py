from django.shortcuts import render
import plotly.express as px
import plotly.graph_objects as go
from django.http import JsonResponse
import pandas as pd
from github import Github
import os

def quick_analysis(request):
    if request.method == 'POST':
        repo_url = request.POST.get('repo_url')
        
        # Extraer usuario y nombre del repositorio de la URL
        parts = repo_url.split('/')
        user = parts[-2]
        repo_name = parts[-1]
        
        # Usar el token de GitHub (asegúrate de tenerlo en las variables de entorno)
        g = Github(os.getenv('GITHUB_TOKEN'))
        
        try:
            repo = g.get_repo(f"{user}/{repo_name}")
            
            # Obtener commits
            commits = repo.get_commits()
            commit_dates = [c.commit.author.date for c in commits]
            commit_authors = [c.commit.author.name for c in commits]
            
            # Gráfico de timeline de commits
            df_commits = pd.DataFrame({
                'fecha': commit_dates,
                'cantidad': 1
            })
            df_commits = df_commits.groupby('fecha').sum().reset_index()
            fig_timeline = px.line(df_commits, x='fecha', y='cantidad',
                                 title='Timeline de Commits')
            
            # Distribución por desarrollador
            df_authors = pd.DataFrame(commit_authors, columns=['autor'])
            fig_authors = px.pie(df_authors['autor'].value_counts().reset_index(),
                               values='autor', names='index',
                               title='Distribución de Commits por Desarrollador')
            
            # Lenguajes utilizados
            languages = repo.get_languages()
            fig_languages = px.pie(
                values=list(languages.values()),
                names=list(languages.keys()),
                title='Distribución de Lenguajes'
            )
            
            # Para las librerías, necesitarías implementar un análisis más detallado
            # Este es un ejemplo simplificado
            libraries = {'React': 30, 'Django': 25, 'NumPy': 20, 'Pandas': 15}
            fig_libraries = px.bar(
                x=list(libraries.keys()),
                y=list(libraries.values()),
                title='Librerías Detectadas'
            )
            
            graphs = {
                'commits_timeline': fig_timeline.to_html(full_html=False),
                'developer_distribution': fig_authors.to_html(full_html=False),
                'languages': fig_languages.to_html(full_html=False),
                'libraries': fig_libraries.to_html(full_html=False)
            }
            
            return render(request, 'quick_analysis.html', {'graphs': graphs})
            
        except Exception as e:
            return render(request, 'quick_analysis.html', 
                        {'error': 'Error al analizar el repositorio'})
    
    return render(request, 'quick_analysis.html') 