# Mensajes de error para el análisis detallado
ANALYSIS_ERROR_MESSAGES = {
    'url_invalid': 'La URL proporcionada no es válida. Por favor, introduce una URL de GitHub válida.',
    'repo_not_found': 'No se pudo encontrar el repositorio. Verifica que la URL sea correcta y el repositorio exista.',
    'briefing_required': 'Por favor, proporciona un archivo briefing para realizar el análisis.',
    'pdf_generation_error': 'Error al generar el informe PDF.',
    'analysis_error': 'Error durante el análisis del repositorio.',
    'file_processing_error': 'Error al procesar el archivo briefing.',
    'general_error': 'Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo.'
}

# Tipos de proyectos
PROJECT_TYPES = {
    'ml': 'Machine Learning',
    'nlp': 'Procesamiento de Lenguaje Natural',
    'genai': 'IA Generativa',
    'web': 'Desarrollo Web',
    'data': 'Análisis de Datos',
    'other': 'Otro'
}

# Configuración de análisis
ANALYSIS_CONFIG = {
    'commit_limit': 1000,  # Límite de commits a analizar
    'branch_limit': 10,    # Límite de ramas a analizar
    'file_size_limit': 10 * 1024 * 1024  # 10MB límite para archivos
} 