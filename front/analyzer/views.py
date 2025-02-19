import os
import fitz  # PyMuPDF
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from reportlab.pdfgen import canvas
from django.http import FileResponse

def home(request):
    return render(request, 'home.html')

def analyze_repository(repo_url, briefing_text):
    """
    Prototype function to simulate repository analysis against a briefing.
    """
    compliance_results = {
        "Essential Level": {
            "Extract files": "✅ Completed",
            "Compare with briefing": "✅ Completed",
            "Basic compliance report": "✅ Completed",
            "Streamlit UI": "❌ Not Implemented",
            "Score": "75%"
        },
        "Medium Level": {
            "Dockerized application": "❌ Not Implemented",
            "Code improvement suggestions": "❌ Not Implemented",
            "API Key for LLM selection": "✅ Implemented",
            "Score": "33%"
        },
        "Advanced Level": {
            "Coding standards evaluation": "❌ Not Implemented",
            "Dependency & vulnerability analysis": "❌ Not Implemented",
            "Score": "0%"
        },
        "Expert Level": {
            "Multi-agent evaluation": "❌ Not Implemented",
            "Semantic analysis of code quality": "❌ Not Implemented",
            "Score": "0%"
        },
        "Overall Compliance Score": "36%"
    }

    technologies_used = ["Python", "Django", "PyMuPDF", "ReportLab"]
    commit_analysis = {
        "Total Commits": 42,
        "Commits by Contributor": {"Alice": 20, "Bob": 12, "Charlie": 10}
    }

    return compliance_results, technologies_used, commit_analysis

def generate_pdf_report(compliance_results, technologies_used, commit_analysis, briefing_name):
    """
    Generate a PDF report of the compliance analysis.
    """
    pdf_name = f"Informe_Básico_{briefing_name}.pdf"
    pdf_path = os.path.join("static/reports", pdf_name)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    c = canvas.Canvas(pdf_path)
    c.setFont("Helvetica", 16)
    c.drawString(100, 800, "Informe básico de cumplimiento del briefing solicitado")
    
    # Commits section
    c.setFont("Helvetica", 14)
    c.drawString(100, 770, "1. Commits Totales")
    c.setFont("Helvetica", 12)
    c.drawString(120, 750, f"Total Commits: {commit_analysis['Total Commits']}")
    y = 730
    for contributor, count in commit_analysis["Commits by Contributor"].items():
        c.drawString(120, y, f"{contributor}: {count} commits")
        y -= 20

    # Technologies section
    c.setFont("Helvetica", 14)
    c.drawString(100, y-10, "2. Lenguajes y Librerías")
    c.setFont("Helvetica", 12)
    y -= 30
    for tech in technologies_used:
        c.drawString(120, y, f"- {tech}")
        y -= 20

    # Compliance Levels
    c.setFont("Helvetica", 14)
    c.drawString(100, y-10, "3. Niveles de cumplimiento del briefing")
    c.setFont("Helvetica", 12)
    y -= 30
    for level, details in compliance_results.items():
        if level == "Overall Compliance Score":
            # Handle the overall score separately
            c.drawString(120, y, f"{level}: {details}")
            y -= 20
        else:
            # Handle other levels (which are dictionaries)
            c.drawString(120, y, f"{level}: {details.get('Score', 'N/A')}")
            y -= 20
            for key, value in details.items():
                if key != "Score":
                    c.drawString(140, y, f"- {key}: {value}")
                    y -= 20

    c.save()
    return pdf_path

def analysis(request):
    compliance_results = {}
    technologies_used = []
    commit_analysis = {}
    pdf_path = None

    if request.method == "POST":
        repo_url = request.POST.get("repo_url")
        briefing_file = request.FILES.get("briefing")

        if briefing_file:
            briefing_name = briefing_file.name.split(".")[0]
            fs = FileSystemStorage()
            file_path = fs.save(f"uploads/{briefing_file.name}", briefing_file)
            full_file_path = fs.path(file_path)

            # Extract text from the PDF
            doc = fitz.open(full_file_path)
            briefing_text = " ".join([page.get_text() for page in doc])

            # Analyze repository
            compliance_results, technologies_used, commit_analysis = analyze_repository(repo_url, briefing_text)

            # Generate a compliance report PDF
            pdf_path = generate_pdf_report(compliance_results, technologies_used, commit_analysis, briefing_name)

    return render(request, "analysis.html", {
        "compliance_results": compliance_results,
        "technologies_used": technologies_used,
        "commit_analysis": commit_analysis,
        "pdf_path": pdf_path
    })