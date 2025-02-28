# Mensajes de error para el análisis rápido
QUICK_ANALYSIS_ERROR_MESSAGES = {
    'url_required': 'Por favor, proporciona una URL del repositorio.',
    'url_invalid': 'La URL proporcionada no es válida.',
    'repo_not_found': 'Repositorio no encontrado.',
    'api_rate_limit': 'Se ha alcanzado el límite de la API de GitHub.',
    'no_commits': 'No se encontraron commits en este repositorio.',
    'auth_error': 'Error de autenticación con GitHub.',
    'general_error': 'Error al analizar el repositorio.'
}

# Configuración de visualización
VISUALIZATION_CONFIG = {
    'graph_colors': [
        '#1f77b4',  # Azul
        '#ff7f0e',  # Naranja
        '#2ca02c',  # Verde
        '#d62728',  # Rojo
        '#9467bd',  # Morado
        '#8c564b',  # Marrón
        '#e377c2',  # Rosa
        '#7f7f7f',  # Gris
        '#bcbd22',  # Amarillo-verde
        '#17becf'   # Cyan
    ],
    'graph_height': 400,
    'graph_width': 800
}

# Bibliotecas principales a detectar
MAIN_LIBRARIES = {
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
    
    # Data Engineering & Web
    'apache-airflow', 'prefect', 'dagster', 'luigi',
    'apache-beam', 'dbt-core', 'great-expectations',
    'feast', 'kedro', 'petl', 'bonobo',
    'sqlalchemy', 'alembic', 'psycopg2-binary',
    'pymongo', 'redis', 'elasticsearch',
    'pyspark', 'findspark', 'koalas',
    'kafka-python', 'confluent-kafka', 'faust-streaming',
    'requests', 'beautifulsoup4', 'selenium', 'scrapy',
    'httpx', 'aiohttp', 'fastapi', 'django',
    
    # Development & Testing
    'pytest', 'unittest', 'nose', 'hypothesis',
    'black', 'flake8', 'pylint', 'mypy',
    'coverage', 'tox', 'pre-commit',
    
    # Utilities & Others
    'python-dotenv', 'pyyaml', 'toml', 'click',
    'typer', 'rich', 'tqdm', 'loguru',
    'pygithub', 'gitpython', 'python-jose',
    'passlib', 'bcrypt', 'cryptography',
    'reportlab', 'pymupdf', 'asgiref',
    'langchain', 'openai', 'transformers',
    'pillow', 'opencv-python', 'numpy'
}

# Configuración de análisis
ANALYSIS_SETTINGS = {
    'max_commits_analyze': 1000,
    'max_files_analyze': 100,
    'max_branches_analyze': 5,
    'commit_analysis_days': 365,  # Análisis del último año
    'language_threshold': 1.0,    # Porcentaje mínimo para mostrar un lenguaje
}

# Tipos de archivos a analizar
FILE_PATTERNS = {
    'requirements': ['requirements.txt', 'requirements/*.txt'],
    'package': ['package.json'],
    'composer': ['composer.json'],
    'docker': ['Dockerfile', 'docker-compose.yml'],
    'ci_cd': ['.github/workflows/*.yml', '.gitlab-ci.yml', 'jenkins*.groovy'],
    'env': ['.env.example', '.env.sample', '.env.template']
} 