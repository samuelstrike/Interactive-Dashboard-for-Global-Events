
let categoryChart, magnitudeChart, frequencyChart;

function showLoading() {
    document.querySelector('.loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.querySelector('.loading-overlay').style.display = 'none';
}

async function initializeCharts() {
    showLoading();
    try {
        const response = await fetch('/api/summary');
        if (!response.ok) throw new Error('Failed to fetch summary data');
        const stats = await response.json();

        console.log('Summary data:', stats); // Debug log

        // Category Chart
        const catCtx = document.getElementById('categoryChart').getContext('2d');
        categoryChart = new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(stats.categories),
                datasets: [{
                    data: Object.values(stats.categories),
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                        '#9966FF', '#FF9F40', '#FF6384', '#36A2EB'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { font: { size: 10 } }
                    }
                }
            }
        });

        // Magnitude Chart
        const magCtx = document.getElementById('magnitudeChart').getContext('2d');
        magnitudeChart = new Chart(magCtx, {
            type: 'bar',
            data: {
                labels: ['Low', 'Medium', 'High'],
                datasets: [{
                    label: 'Event Count',
                    data: [
                        stats.magnitudes.low || 0,
                        stats.magnitudes.medium || 0,
                        stats.magnitudes.high || 0
                    ],
                    backgroundColor: ['#FFEB3B', '#FF9800', '#F44336']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Frequency Chart
        const freqCtx = document.getElementById('frequencyChart').getContext('2d');
        frequencyChart = new Chart(freqCtx, {
            type: 'line',
            data: {
                labels: Object.keys(stats.daily_counts),
                datasets: [{
                    label: 'Daily Events',
                    data: Object.values(stats.daily_counts),
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    },
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error initializing charts:', error);
    } finally {
        hideLoading();
    }
}

async function updateCharts() {
    try {
        const response = await fetch('/api/summary');
        if (!response.ok) throw new Error('Failed to fetch summary data');
        const stats = await response.json();

        console.log('Update data:', stats); // Debug log

        if (categoryChart) {
            categoryChart.data.labels = Object.keys(stats.categories);
            categoryChart.data.datasets[0].data = Object.values(stats.categories);
            categoryChart.update();
        }

        if (magnitudeChart) {
            magnitudeChart.data.datasets[0].data = [
                stats.magnitudes.low || 0,
                stats.magnitudes.medium || 0,
                stats.magnitudes.high || 0
            ];
            magnitudeChart.update();
        }

        if (frequencyChart) {
            frequencyChart.data.labels = Object.keys(stats.daily_counts);
            frequencyChart.data.datasets[0].data = Object.values(stats.daily_counts);
            frequencyChart.update();
        }
    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

function initializeSlider() {
    const slider = document.getElementById('magnitudeSlider');
    if (slider.noUiSlider) {
        slider.noUiSlider.destroy();
    }
    
    noUiSlider.create(slider, {
        start: [0, 10],
        connect: true,
        range: {
            'min': 0,
            'max': 10
        },
        step: 0.1
    });

    slider.noUiSlider.on('update', values => {
        document.getElementById('magnitudeValues').innerHTML = 
            `Range: ${Number(values[0]).toFixed(1)} - ${Number(values[1]).toFixed(1)}`;
    });

    return slider;
}

async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        if (!response.ok) throw new Error('Failed to fetch categories');
        const data = await response.json();
        
        const select = document.getElementById('eventType');
        data.categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.title;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

async function refreshData() {
    showLoading();
    try {
        await Promise.all([
            updateCharts(),
            updateMap()
        ]);
    } catch (error) {
        console.error('Error refreshing data:', error);
    } finally {
        hideLoading();
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing charts...'); // Debug log
    initializeCharts();
    initializeSlider();
    loadCategories();
});
