![RepoScope Banner](RepoScope.gif)

# RepoScope: Analizador de Repositorios GitHub Potenciado por IA

## Sobre el Proyecto

RepoScope nace como proyecto final del Bootcamp de AI de Factoria F5. Este proyecto responde a una necesidad real planteada por Factoria F5 como stakeholder: desarrollar una herramienta que permita analizar de forma automatizada los repositorios de los estudiantes, evaluando el cumplimiento técnico y proporcionando feedback detallado sobre sus proyectos.

### Contexto del Proyecto

Como parte del proceso de evaluación en Factoria F5, los formadores necesitan revisar numerosos repositorios de estudiantes para evaluar sus competencias técnicas. RepoScope automatiza este proceso utilizando inteligencia artificial y técnicas avanzadas de análisis de código, permitiendo:

- Evaluación objetiva del cumplimiento de requisitos técnicos
- Análisis automático de patrones de código y buenas prácticas
- Generación de informes detallados para formadores y estudiantes
- Visualización clara del progreso y áreas de mejora

## Equipo de Desarrollo

Este proyecto ha sido desarrollado por el equipo P3 del Bootcamp AI:

- [Alberto Carrillo](https://github.com/carrillo-p) - 
- [Vittoria De Novellis](https://github.com/Dolcevitta95) - 
- [Andrea Moraleda Blanco](https://github.com/AndreaMoraledaBlanco) - 
- [Esther Tapias Paez-Camino](https://github.com/EstherTapias) - 
- [Isabel Teruel](https://github.com/isabel-teruel) - 

## Descripción del Proyecto

El **Analizador de Repositorios GitHub Potenciado por IA** es una herramienta avanzada que combina análisis de código, procesamiento de lenguaje natural y visualización de datos para proporcionar una evaluación completa de repositorios GitHub. El sistema utiliza múltiples modelos de IA (Groq, Ollama) y técnicas de RAG (Retrieval Augmented Generation) para generar análisis detallados y contextualizados.

## Componentes Principales

### 1. RAG_analyzer.py
- Implementa el análisis principal usando modelos de lenguaje (Groq/Ollama)
- Gestiona la integración con diferentes modelos de IA
- Procesa y analiza el contenido del repositorio
- Genera informes detallados de cumplimiento técnico

### 2. RAG_process.py
- Filtra archivos relevantes del repositorio.
- Detecta tecnologías utilizadas en el repositorio.
- Genera embeddings para el contenido del repositorio y el briefing.
- Permite realizar búsquedas semánticas en el contenido procesado.


### 3. github_getter.py
- Maneja la interacción con la API de GitHub
- Extrae estadísticas detalladas del repositorio
- Analiza commits, contribuciones y lenguajes
- Genera visualizaciones de actividad del repositorio

### 4. briefing_analyzer.py
- Procesa y analiza documentos de briefing
- Utiliza embeddings para comparar requisitos con implementación
- Evalúa el cumplimiento de objetivos técnicos
- Genera métricas de conformidad

### 5. Interfaz Web (views.py)
- Proporciona una interfaz interactiva para el análisis
- Permite análisis rápidos y detallados
- Genera visualizaciones interactivas con Plotly
- Exporta informes en formato PDF

## Características Principales

1. **Análisis Multinivel**
   - Evaluación de código y estructura
   - Análisis de patrones y prácticas de desarrollo
   - Detección de tecnologías y frameworks
   - Métricas de calidad y complejidad

2. **Visualizaciones Avanzadas**
   - Gráficos de actividad de commits
   - Distribución de contribuciones
   - Análisis de lenguajes de programación
   - Estadísticas de desarrollo

3. **Generación de Informes**
   - Informes técnicos detallados en PDF
   - Evaluación de cumplimiento de requisitos
   - Recomendaciones de mejora
   - Análisis de madurez técnica

## Configuración del Entorno

### A. Instalación Local

1. **Requisitos Previos**
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Variables de Entorno**
   Crea un archivo `.env` con las siguientes variables:
   ```
   GITHUB_API_KEY=tu_token_de_github
   GROQ_API_KEY=tu_clave_de_groq
   ```

3. **Modelos de IA**
   - Configuración de Groq (principal)
   - Fallback a Ollama (local)
   - Embeddings de Hugging Face

### B. Instalación con Docker

1. **Construir la Imagen**
   ```bash
   # Clonar el repositorio
   git clone https://github.com/tu-usuario/GitHub_Analyzer.git
   cd GitHub_Analyzer

   # Construir la imagen Docker
   docker build -t github-analyzer .
   ```

2. **Ejecutar el Contenedor**
   ```bash
   docker run -d \
     -p 8000:8000 \
     -e GITHUB_API_KEY=tu_token_de_github \
     -e GROQ_API_KEY=tu_clave_de_groq \
     --name github-analyzer \
     github-analyzer
   ```

3. **Acceder a la Aplicación**
   - Abre tu navegador y visita `http://localhost:8000`

4. **Gestión del Contenedor**
   ```bash
   # Detener el contenedor
   docker stop github-analyzer

   # Iniciar el contenedor
   docker start github-analyzer

   # Ver logs
   docker logs -f github-analyzer
   ```

## Obtención de Claves API

### 1. GitHub API Key

1. **Acceso a GitHub**
   - Inicia sesión en tu cuenta de [GitHub](https://github.com)
   - Ve a Configuración (Settings) desde el menú desplegable de tu perfil

2. **Crear Token de Acceso**
   - Navega a `Settings > Developer settings > Personal access tokens > Tokens (classic)`
   - Haz clic en "Generate new token (classic)"
   - Selecciona "Generate new token (classic)"

3. **Configurar Permisos**
   - Nombre descriptivo: "GitHub Analyzer Access"
   - Selecciona los siguientes permisos:
     - `repo` (acceso completo a repositorios)
     - `read:user` (lectura de información del usuario)
     - `read:org` (opcional, para repositorios de organizaciones)

4. **Generar y Guardar**
   - Haz clic en "Generate token"
   - **¡IMPORTANTE!** Copia y guarda el token inmediatamente
   - Este token solo se muestra una vez y no podrás verlo nuevamente

### 2. Groq API Key

1. **Crear Cuenta en Groq**
   - Visita [Groq Cloud Console](https://console.groq.com)
   - Regístrate para una nueva cuenta o inicia sesión

2. **Obtener API Key**
   - Ve al panel de control de Groq
   - Navega a la sección "API Keys"
   - Haz clic en "Create New API Key"

3. **Configurar la API Key**
   - Asigna un nombre descriptivo a tu key
   - Selecciona el modelo que usarás (mixtral-8x7b-32768)
   - Define límites de uso si lo deseas

4. **Guardar la API Key**
   - Copia la API key generada
   - Guárdala de forma segura
   - No la compartas ni la expongas públicamente

## Uso del Sistema

1. **Análisis Rápido**
   ```python
   from github_getter import GitHubAnalyzer
   
   analyzer = GitHubAnalyzer()
   stats = analyzer.get_repo_stats("URL_DEL_REPOSITORIO")
   ```

2. **Análisis Completo**
   ```python
   from RAG_analyzer import GitHubRAGAnalyzer
   
   analyzer = GitHubRAGAnalyzer()
   results = analyzer.analyze_requirements_completion(
       repo_url="URL_DEL_REPOSITORIO",
       briefing_path="RUTA_AL_BRIEFING"
   )
   ```

## Ejemplos de Uso

### 1. Análisis Rápido de Repositorio
```python
# Ejemplo de análisis rápido
from github_getter import GitHubAnalyzer

analyzer = GitHubAnalyzer()
repo_url = "https://github.com/usuario/repositorio"
stats = analyzer.get_repo_stats(repo_url)

# Visualizar estadísticas
print(f"Total de commits: {stats['commit_count']}")
print(f"Lenguajes detectados: {stats['languages']}")
```

### 2. Análisis Completo con Briefing
```python
# Ejemplo de análisis completo
from RAG_analyzer import GitHubRAGAnalyzer

analyzer = GitHubRAGAnalyzer()
results = analyzer.analyze_requirements_completion(
    repo_url="https://github.com/usuario/repositorio",
    briefing_path="ruta/al/briefing.pdf"
)

# Acceder a los resultados
print(f"Evaluación general: {results['tier_analysis']['evaluacion_general']}")
```

### 3. Uso desde la Interfaz Web
1. Inicia el servidor Django:
   ```bash
   python manage.py runserver
   ```
2. Accede a `http://localhost:8000` en tu navegador
3. Ingresa la URL del repositorio y sube el archivo de briefing
4. Visualiza los resultados y descarga el informe PDF

## Tecnologías Utilizadas

- **Análisis de Código**: Python, PyDriller
- **Modelos de IA**: Groq, Ollama, Hugging Face
- **Visualización**: Plotly, Seaborn
- **Web**: Django
- **Procesamiento de Datos**: Pandas, NumPy
- **Embeddings**: FAISS, sentence-transformers
- **Documentos**: ReportLab, PyMuPDF

## Contribución

1. Fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

