from django.shortcuts import render
import plotly.express as px
import plotly.graph_objects as go
from django.http import FileResponse, Http404
import pandas as pd
import sys
import os
import logging

import time
import shutil
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
from github_getter import GitHubAnalyzer

logger = logging.getLogger('repo_analyzer.views')

def create_analysis_visualizations(all_commits, commit_authors, repo, analyzer, repo_url):
    logger.info(f"Found {len(all_commits)} total commits")

    # Get complete repository statistics using GitHubAnalyzer
    repo_stats = analyzer.get_repo_stats(repo_url)
    
    # 1. Generate commit activity visualization
    logger.info("Generating commit activity visualization")
    
    # Commitment activity data preparation
    commit_data = pd.DataFrame({
        'fecha': [c.commit.author.date.date() for c in all_commits],
        'autor': commit_authors,
        'hora': [c.commit.author.date.hour for c in all_commits],
        'cantidad': 1
    })

    # Activity chart creation
    fig_activity = go.Figure()
    colors = px.colors.qualitative.Set1

    # Time series generation by author
    for idx, autor in enumerate(commit_data['autor'].unique()):
        df_autor = commit_data[commit_data['autor'] == autor]
        df_daily = df_autor.groupby('fecha')['cantidad'].sum().reset_index()
        
        # Fill in missing dates
        fecha_min = commit_data['fecha'].min()
        fecha_max = commit_data['fecha'].max()
        todas_fechas = pd.date_range(start=fecha_min, end=fecha_max, freq='D').date
        
        df_completo = pd.DataFrame({'fecha': todas_fechas})
        df_completo = df_completo.merge(df_daily, on='fecha', how='left')
        df_completo['cantidad'] = df_completo['cantidad'].fillna(0)
        
        # Add time series to chart
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

    # Configure activity chart layout
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

    # 2. Generate developer distribution chart
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
        logger.error(f"Error creating developer distribution chart: {str(e)}")
        fig_authors = go.Figure()
        fig_authors.add_annotation(
            text=f"Error al procesar la distribución de commits: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )

    # 3. Libraries visualization - NEW!
    libraries_data = repo_stats.get('libraries', [])
    fig_libraries = go.Figure()

    try:
        if libraries_data:
            # Group libraries by category
            libraries_df = pd.DataFrame(libraries_data)
            
            libraries_df_sorted = libraries_df.sort_values(['category', 'name'])
            
            # Create bar chart of libraries by category
            fig_libraries = px.bar(
                libraries_df_sorted,
                x='category',
                y='name',
                color='category',
                title='Bibliotecas por Categoría',
                labels={'name': 'Biblioteca', 'category': 'Categoría'},
                height=max(400, len(libraries_df) * 20),  # Dynamic height based on library count
                orientation='h'  # Horizontal bars for better readability
            )
            
            fig_libraries.update_layout(
                barmode='group',
                xaxis_title="Categoría",
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False
            )
        else:
            fig_libraries.add_annotation(
                text="No se detectaron bibliotecas en este repositorio",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
    except Exception as e:
        logger.error(f"Error creating libraries visualization: {str(e)}")
        fig_libraries.add_annotation(
            text=f"Error al visualizar bibliotecas: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )

    # 4. Prepare and return context with all visualizations
    context = {
        'graphs': {
            'commits_activity': fig_activity.to_html(full_html=False, include_plotlyjs=True),
            'developer_distribution': fig_authors.to_html(full_html=False, include_plotlyjs=True),
            'libraries_distribution': fig_libraries.to_html(full_html=False, include_plotlyjs=True),
        },
        'languages': repo_stats.get('languages', []),
        'libraries': repo_stats.get('libraries', [])
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
    
def download_pdf(request, filename):
    """Vista para descargar archivos PDF"""
    try:
        file_path = os.path.join('static/reports', filename)
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            logger.error(f"PDF file not found: {file_path}")
            raise Http404("El archivo PDF no existe")
    except Exception as e:
        logger.error(f"Error al descargar el PDF {filename}: {str(e)}")
        raise Http404("Error al descargar el archivo PDF")