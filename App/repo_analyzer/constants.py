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
    'python': [
        'django', 'flask', 'fastapi', 'pandas', 'numpy',
        'tensorflow', 'pytorch', 'scikit-learn', 'matplotlib',
        'seaborn', 'plotly', 'requests', 'beautifulsoup4'
    ],
    'javascript': [
        'react', 'vue', 'angular', 'express', 'next',
        'nuxt', 'gatsby', 'jest', 'mocha', 'chai'
    ],
    'php': [
        'laravel', 'symfony', 'wordpress', 'phpunit',
        'composer', 'guzzle', 'monolog'
    ]
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