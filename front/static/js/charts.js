// Función para inicializar los gráficos
function initializeCharts(data) {
    // Gráfico de commits totales
    const commitsCtx = document.getElementById('commitsChart').getContext('2d');
    new Chart(commitsCtx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Commits Totales',
                data: data.commits,
                borderColor: '#FF6B35',
                tension: 0.1
            }]
        },
        options: {
            responsive: true
        }
    });

    // Gráfico de distribución de commits por desarrollador
    const contributorsCtx = document.getElementById('contributorsChart').getContext('2d');
    new Chart(contributorsCtx, {
        type: 'pie',
        data: {
            labels: data.contributors,
            datasets: [{
                data: data.contributionsPercentage,
                backgroundColor: [
                    '#FF6B35',
                    '#FF8B60',
                    '#FFB088',
                    '#FFD5B8',
                    '#FFE8D6'
                ]
            }]
        },
        options: {
            responsive: true
        }
    });

    // Gráfico de lenguajes utilizados
    const languagesCtx = document.getElementById('languagesChart').getContext('2d');
    new Chart(languagesCtx, {
        type: 'bar',
        data: {
            labels: data.languages,
            datasets: [{
                label: 'Uso de Lenguajes',
                data: data.languagePercentages,
                backgroundColor: '#FF6B35'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
} 