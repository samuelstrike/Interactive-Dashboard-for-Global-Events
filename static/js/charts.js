
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
                labels: ['Low (0-1.5)', 'Medium (1.5-5.0)', 'High (5.0+)'],
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
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `Events: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Events'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Magnitude Range'
                        }
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
        start: [0, 20],
        connect: true,
        range: {
            'min': 0,
            'max': 20
        },
        step: 0.5,
        tooltips: true
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

async function updateMap() {
    showLoading();
    try {
        const slider = document.getElementById('magnitudeSlider');
        const [minMag, maxMag] = slider.noUiSlider.get();

        const params = new URLSearchParams({
            start_date: document.getElementById('startDate').value,
            end_date: document.getElementById('endDate').value,
            event_type: document.getElementById('eventType').value,
            min_magnitude: minMag,
            max_magnitude: maxMag
        });

        const response = await fetch(`/api/map?${params}`);
        if (!response.ok) throw new Error('Failed to update map');

        const mapHtml = await response.text();
        document.querySelector('.map-container').innerHTML = mapHtml;
    } catch (error) {
        console.error('Error updating map:', error);
    } finally {
        hideLoading();
    }
}

async function refreshData() {
    showLoading();
    try {
        // Update both map and charts
        await Promise.all([
            updateMap(),
            updateCharts()
        ]);
    } catch (error) {
        console.error('Error refreshing data:', error);
    } finally {
        hideLoading();
    }
}

// Initialize everything when the document is ready
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await initializeCharts();
        await loadCategories();
        initializeSlider();

        // Set default date range
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);  // Last 30 days

        document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
        document.getElementById('startDate').value = startDate.toISOString().split('T')[0];

        // Add event listeners
        document.getElementById('magnitudeSlider').noUiSlider.on('change', refreshData);
        document.getElementById('eventType').addEventListener('change', refreshData);
        document.getElementById('startDate').addEventListener('change', refreshData);
        document.getElementById('endDate').addEventListener('change', refreshData);

        // Initial data load
        await refreshData();
    } catch (error) {
        console.error('Error during initialization:', error);
    }
});
