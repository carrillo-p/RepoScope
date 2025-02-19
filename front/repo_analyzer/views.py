from django.shortcuts import render
import plotly.express as px
import plotly.graph_objects as go
from django.http import JsonResponse
import pandas as pd
from github import Github
import os
from django.contrib import messages
import json

def quick_analysis(request):
    if request.method == 'POST':
        repo_url = request.POST.get('repo_url')
        
        if not repo_url:
            messages.error(request, 'Por favor, proporciona una URL válida')
            return render(request, 'quick_analysis.html')
            
        try:
            # Limpiar la URL y extraer usuario/repo
            repo_url = repo_url.strip()
            if repo_url.endswith('/'):
                repo_url = repo_url[:-1]
            parts = repo_url.split('/')
            if 'github.com' not in repo_url:
                messages.error(request, 'Por favor, proporciona una URL válida de GitHub')
                return render(request, 'quick_analysis.html')
                
            user = parts[-2]
            repo_name = parts[-1]
            
            # Obtener token de GitHub
            github_token = os.getenv('GITHUB_TOKEN')
            if not github_token:
                messages.error(request, 'Error de configuración: Token de GitHub no encontrado')
                return render(request, 'quick_analysis.html')
            
            g = Github(github_token)
            
            try:
                repo = g.get_repo(f"{user}/{repo_name}")
            except Exception as e:
                messages.error(request, f'No se pudo acceder al repositorio: {str(e)}')
                return render(request, 'quick_analysis.html')
            
            # Obtener commits
            try:
                # Obtener todas las ramas
                branches = repo.get_branches()
                all_commits = []
                commit_authors = []
                
                # Recolectar commits de todas las ramas
                for branch in branches:
                    branch_commits = repo.get_commits(sha=branch.name)
                    for commit in branch_commits:
                        # Evitar contar commits duplicados que existen en múltiples ramas
                        if commit.sha not in [c.sha for c in all_commits]:
                            all_commits.append(commit)
                            # Usar el login de GitHub en lugar del nombre
                            author = None
                            if commit.author:  # Si el autor tiene cuenta de GitHub
                                author = commit.author.login
                            elif commit.commit.author.email:  # Si no tiene cuenta, usar email
                                author = commit.commit.author.email
                            else:  # Si no hay email, usar el nombre
                                author = commit.commit.author.name
                            commit_authors.append(author)

                if not all_commits:
                    messages.warning(request, 'No se encontraron commits en este repositorio')
                    return render(request, 'quick_analysis.html')
                
                # Gráfico de actividad por fecha y hora
                commit_data = pd.DataFrame({
                    'fecha': [c.commit.author.date.date() for c in all_commits],
                    'autor': commit_authors,
                    'hora': [c.commit.author.date.hour for c in all_commits],
                    'cantidad': 1
                })

                # Crear figura base
                fig_activity = go.Figure()

                # Colores para cada desarrollador
                colors = px.colors.qualitative.Set1

                # Añadir una línea por cada autor
                for idx, autor in enumerate(commit_data['autor'].unique()):
                    df_autor = commit_data[commit_data['autor'] == autor]
                    
                    # Agrupar por fecha y contar commits
                    df_daily = df_autor.groupby('fecha')['cantidad'].sum().reset_index()
                    
                    # Asegurarse de que tenemos todas las fechas
                    fecha_min = commit_data['fecha'].min()
                    fecha_max = commit_data['fecha'].max()
                    todas_fechas = pd.date_range(start=fecha_min, end=fecha_max, freq='D').date
                    
                    # Crear DataFrame completo con todas las fechas
                    df_completo = pd.DataFrame({'fecha': todas_fechas})
                    df_completo = df_completo.merge(df_daily, on='fecha', how='left')
                    df_completo['cantidad'] = df_completo['cantidad'].fillna(0)
                    
                    # Añadir línea para este autor
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

                # Configurar el layout
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
                
                # Distribución por desarrollador
                try:
                    df_authors = pd.DataFrame(commit_authors, columns=['autor'])
                    author_counts = df_authors['autor'].value_counts()
                    
                    # Calcular porcentajes
                    total_commits = len(all_commits)
                    author_percentages = (author_counts / total_commits * 100).round(2)
                    
                    fig_authors = px.pie(
                        values=author_counts.values,
                        names=author_counts.index,
                        title=f'Distribución de Commits por Desarrollador (Total: {total_commits})',
                        hover_data=[author_percentages]
                    )
                    
                    # Mejorar el formato del hover
                    fig_authors.update_traces(
                        hovertemplate="<b>%{label}</b><br>" +
                        "Commits: %{value}<br>" +
                        "Porcentaje: %{customdata:.1f}%<br>"
                    )
                    
                    # Ordenar las secciones por tamaño
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
                
                # Lenguajes utilizados
                languages = repo.get_languages()
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
                else:
                    languages_data = []

                # Detección de librerías
                libraries_data = []
                main_libraries = {
                    # Python - Frameworks Web
                    'django', 'flask', 'fastapi', 'pyramid', 'tornado', 'starlette',
                    'aiohttp', 'sanic', 'bottle', 'dash',
                    
                    # Data Analysis
                    'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn',
                    'plotly', 'bokeh', 'altair', 'streamlit',
                    'statsmodels', 'patsy', 'polars', 'vaex',
                    'ydata-profiling', 'great-expectations',
                    'dask', 'modin', 'koalas',
                    
                    # Data Science & Machine Learning
                    'scikit-learn', 'tensorflow', 'pytorch', 'keras',
                    'xgboost', 'lightgbm', 'catboost', 'rapids',
                    'transformers', 'spacy', 'gensim', 'nltk',
                    'opencv-python', 'pillow', 'scikit-image',
                    'imbalanced-learn', 'optuna', 'hyperopt',
                    'shap', 'lime', 'eli5', 'mlflow',
                    'tensorboard', 'wandb', 'neptune-client',
                    
                    # Data Engineering
                    'apache-airflow', 'prefect', 'dagster', 'luigi',
                    'apache-beam', 'dbt-core', 'great-expectations',
                    'feast', 'kedro', 'petl', 'bonobo',
                    'sqlalchemy', 'alembic', 'psycopg2-binary',
                    'pymongo', 'redis', 'elasticsearch',
                    'pyspark', 'findspark', 'koalas',
                    'kafka-python', 'confluent-kafka', 'faust-streaming',
                    
                    # Big Data & Cloud
                    'boto3', 'google-cloud', 'azure-storage',
                    'snowflake-connector-python', 'databricks-cli',
                    'delta-spark', 'pyarrow', 'fastparquet',
                    'dask', 'ray', 'modin', 'vaex',
                    
                    # Data Quality & Testing
                    'pytest', 'unittest', 'nose', 'hypothesis',
                    'great-expectations', 'pandera', 'cerberus',
                    'faker', 'coverage', 'pylint', 'black',
                    
                    # Data Visualization
                    'plotly', 'bokeh', 'altair', 'seaborn',
                    'matplotlib', 'dash', 'streamlit', 'gradio',
                    'holoviews', 'geoplotlib', 'folium', 'geopandas',
                    
                    # ETL & Data Processing
                    'beautifulsoup4', 'scrapy', 'selenium',
                    'requests', 'aiohttp', 'httpx',
                    'pandas', 'numpy', 'polars', 'dask',
                    'pyarrow', 'fastparquet', 'python-snappy',
                    
                    # Time Series
                    'prophet', 'statsmodels', 'pmdarima',
                    'neuralprophet', 'sktime', 'tslearn',
                    'pyts', 'tsfresh', 'stumpy',
                    
                    # Deep Learning
                    'tensorflow', 'torch', 'keras',
                    'transformers', 'pytorch-lightning',
                    'fastai', 'mxnet', 'jax', 'flax',
                    
                    # MLOps & Deployment
                    'mlflow', 'kubeflow', 'bentoml', 'ray[serve]',
                    'streamlit', 'gradio', 'dash',
                    'fastapi', 'flask', 'docker',
                    'kubernetes', 'seldon-core', 'triton',
                    
                    # Experiment Tracking
                    'mlflow', 'wandb', 'neptune-client',
                    'tensorboard', 'sacred', 'comet-ml',
                    
                    # Feature Stores
                    'feast', 'hopsworks', 'tecton',
                    
                    # Model Monitoring
                    'evidently', 'whylogs', 'arize',
                    'great-expectations', 'deepchecks',
                    
                    # AutoML
                    'auto-sklearn', 'autokeras', 'pycaret',
                    'tpot', 'automl-gs', 'flaml', 'ludwig'
                }

                try:
                    # Intentar leer requirements.txt para Python
                    requirements = repo.get_contents("requirements.txt")
                    content = requirements.decoded_content.decode()
                    for line in content.split('\n'):
                        if '==' in line:
                            name, version = line.split('==')
                            name = name.strip().lower()
                            # Solo añadir si es una librería principal
                            if name in main_libraries:
                                libraries_data.append({
                                    'name': name,
                                    'version': version.strip(),
                                    'type': 'Python'
                                })
                except:
                    pass

                try:
                    # Intentar leer package.json para JavaScript
                    package_json = repo.get_contents("package.json")
                    content = json.loads(package_json.decoded_content.decode())
                    
                    # Analizar dependencies y devDependencies
                    all_deps = {}
                    if 'dependencies' in content:
                        all_deps.update(content['dependencies'])
                    if 'devDependencies' in content:
                        all_deps.update(content['devDependencies'])
                    
                    for lib, version in all_deps.items():
                        lib_name = lib.lower()
                        # Solo añadir si es una librería principal
                        if lib_name in main_libraries:
                            libraries_data.append({
                                'name': lib,
                                'version': version.replace('^', '').replace('~', ''),
                                'type': 'JavaScript'
                            })
                except:
                    pass

                try:
                    # Intentar leer composer.json para PHP
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

                # Ordenar librerías por tipo y nombre
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
                messages.error(request, f'Error al procesar los datos del repositorio: {str(e)}')
                return render(request, 'quick_analysis.html')
                
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
            return render(request, 'quick_analysis.html')
    
    return render(request, 'quick_analysis.html') 