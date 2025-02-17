from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def analysis(request):
    if request.method == 'POST':
        # Aquí irá la lógica para procesar el repositorio
        pass
    return render(request, 'analysis.html') 