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
    Mock function to check repository compliance against a briefing.
    """
    compliance_results = {
        "README.md": "✅ Present",
        "app.py": "✅ Present",
        "requirements.txt": "❌ Missing",
        "test.py": "⚠️ Not Required but Useful",
        "Overall Compliance Score": "67%"
    }
    return compliance_results

def generate_pdf_report(compliance_results):
    """
    Generate a PDF report of the compliance analysis.
    """
    pdf_path = "static/reports/compliance_report.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    c = canvas.Canvas(pdf_path)
    c.setFont("Helvetica", 16)
    c.drawString(100, 800, "Informe de Cumplimiento - RepoAnalyzer")
    
    c.setFont("Helvetica", 12)
    y = 760
    for key, value in compliance_results.items():
        c.drawString(100, y, f"{key}: {value}")
        y -= 20

    c.save()
    return pdf_path

def analysis(request):
    compliance_results = {}
    pdf_path = None

    if request.method == "POST":
        repo_url = request.POST.get("repo_url")
        briefing_file = request.FILES.get("briefing")

        if briefing_file:
            fs = FileSystemStorage()
            file_path = fs.save(f"uploads/{briefing_file.name}", briefing_file)
            full_file_path = fs.path(file_path)

            # Extract text from the PDF
            doc = fitz.open(full_file_path)
            briefing_text = " ".join([page.get_text() for page in doc])

            # Analyze repository based on extracted briefing text
            compliance_results = analyze_repository(repo_url, briefing_text)

            # Generate a compliance report PDF
            pdf_path = generate_pdf_report(compliance_results)

    return render(request, "analysis.html", {"compliance_results": compliance_results, "pdf_path": pdf_path}) 