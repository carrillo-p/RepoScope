from django.shortcuts import render
import plotly.express as px
import plotly.graph_objects as go
from django.http import JsonResponse
import pandas as pd
from django.contrib import messages
import json
from Github_getter import GitHubAnalyzer

def quick_analysis(request):
    if request.method == 'POST':
        repo_url = request.POST.get('repo_url')
        
        if not repo_url:
            messages.error(request, 'Por favor, proporciona una URL válida')
            return render(request, 'quick_analysis.html')
            
        try:
            # Initialize analyzer
            analyzer = GitHubAnalyzer()
            repo = analyzer.github.get_repo(analyzer._extract_repo_name(repo_url))
            
            # Get all commits and authors
            branches = repo.get_branches()
            all_commits = []
            commit_authors = []
            
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

            if not all_commits:
                messages.warning(request, 'No se encontraron commits en este repositorio')
                return render(request, 'quick_analysis.html')
            
            # Create activity graph
            commit_data = pd.DataFrame({
                'fecha': [c.commit.author.date.date() for c in all_commits],
                'autor': commit_authors,
                'hora': [c.commit.author.date.hour for c in all_commits],
                'cantidad': 1
            })

            # Create base figure
            fig_activity = go.Figure()
            colors = px.colors.qualitative.Set1

            for idx, autor in enumerate(commit_data['autor'].unique()):
                df_autor = commit_data[commit_data['autor'] == autor]
                df_daily = df_autor.groupby('fecha')['cantidad'].sum().reset_index()
                
                fecha_min = commit_data['fecha'].min()
                fecha_max = commit_data['fecha'].max()
                todas_fechas = pd.date_range(start=fecha_min, end=fecha_max, freq='D').date
                
                df_completo = pd.DataFrame({'fecha': todas_fechas})
                df_completo = df_completo.merge(df_daily, on='fecha', how='left')
                df_completo['cantidad'] = df_completo['cantidad'].fillna(0)
                
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

            # Developer distribution
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

            # Get languages data
            languages = repo.get_languages()
            languages_data = []
            if languages:
                total_bytes = sum(languages.values())
                languages_data = [
                    {
                        'name': lang,
                        'percentage': round((bytes_count / total_bytes) * 100, 1),
                        'color': px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
                    }
                    for i, (lang, bytes_count) in enumerate(sorted(
                        languages.items(),
                        key=lambda x: x[1],
                        reverse=True
                    ))
                ]

            # Libraries detection
            libraries_data = []
            main_libraries = {
                # [Your existing main_libraries set]
                # Keep the existing library definitions here
            }

            # Python requirements.txt
            try:
                requirements = repo.get_contents("requirements.txt")
                content = requirements.decoded_content.decode()
                for line in content.split('\n'):
                    if '==' in line:
                        name, version = line.split('==')
                        name = name.strip().lower()
                        if name in main_libraries:
                            libraries_data.append({
                                'name': name,
                                'version': version.strip(),
                                'type': 'Python'
                            })
            except:
                pass

            # JavaScript package.json
            try:
                package_json = repo.get_contents("package.json")
                content = json.loads(package_json.decoded_content.decode())
                all_deps = {}
                if 'dependencies' in content:
                    all_deps.update(content['dependencies'])
                if 'devDependencies' in content:
                    all_deps.update(content['devDependencies'])
                
                for lib, version in all_deps.items():
                    lib_name = lib.lower()
                    if lib_name in main_libraries:
                        libraries_data.append({
                            'name': lib,
                            'version': version.replace('^', '').replace('~', ''),
                            'type': 'JavaScript'
                        })
            except:
                pass

            # PHP composer.json
            try:
                composer_json = repo.get_contents("composer.json")
                content = json.loads(composer_json.decoded_content.decode())
                if 'require' in content:
                    for lib, version in content['require'].items():
                        lib_name = lib.lower()
                        if lib_name in main_libraries:
                            libraries_data.append({
                                'name': lib,
                                'version': version,
                                'type': 'PHP'
                            })
            except:
                pass

            libraries_data.sort(key=lambda x: (x['type'], x['name']))

            context = {
                'graphs': {
                    'commits_activity': fig_activity.to_html(full_html=False),
                    'developer_distribution': fig_authors.to_html(full_html=False)
                },
                'languages': languages_data,
                'libraries': libraries_data
            }

            return render(request, 'quick_analysis.html', context)
                
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return render(request, 'quick_analysis.html')
    
    return render(request, 'quick_analysis.html')