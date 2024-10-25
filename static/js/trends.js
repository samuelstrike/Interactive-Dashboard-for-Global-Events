
let trendsChart;
let currentPeriod = 'daily';

// Utility Functions
function showLoading() {
    document.querySelector('.loading').style.display = 'flex';
}

function hideLoading() {
    document.querySelector('.loading').style.display = 'none';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(date);
}

// Initialize Chart
function initializeTrendsChart() {
    const ctx = document.getElementById('trendsChart').getContext('2d');
    if (trendsChart) {
        trendsChart.destroy();
    }

    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Event Count',
                data: [],
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                fill: true,
                tension: 0.4
            }, {
                label: 'Trend Line',
                data: [],
                borderColor: '#dc3545',
                borderDash: [5, 5],
                fill: false,
                tension: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Event Frequency Over Time',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    callbacks: {
                        title: (context) => formatDate(context[0].label)
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
                        text: 'Time Period'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// Load Categories
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        if (!response.ok) throw new Error('Failed to fetch categories');
        
        const data = await response.json();
        const select = document.getElementById('categorySelect');
        
        // Clear existing options except the first one
        while (select.options.length > 1) {
            select.remove(1);
        }
        
        data.categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.title;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
        showError('Failed to load categories');
    }
}

// Update Chart Data
async function updateTrendsData() {
    showLoading();
    try {
        const category = document.getElementById('categorySelect').value;
        const response = await fetch(`/api/trends?category=${category}&period=${currentPeriod}`);
        if (!response.ok) throw new Error('Failed to fetch trend data');
        
        const data = await response.json();
        
        // Update chart
        trendsChart.data.labels = data.periods;
        trendsChart.data.datasets[0].data = data.counts;
        
        // Calculate and update trend line
        if (data.counts.length > 1) {
            const trendLine = calculateTrendLine(data.counts);
            trendsChart.data.datasets[1].data = trendLine;
        }
        
        trendsChart.options.plugins.title.text = 
            `Event Frequency (${currentPeriod.charAt(0).toUpperCase() + currentPeriod.slice(1)})`;
        trendsChart.update();

        // Update statistics
        updateStatistics(data);
    } catch (error) {
        console.error('Error updating trends:', error);
        showError('Failed to update trend data');
    } finally {
        hideLoading();
    }
}

// Calculate Trend Line
function calculateTrendLine(data) {
    const n = data.length;
    if (n < 2) return data;

    // Calculate the sum of x, y, xy and x^2
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumXX = 0;

    data.forEach((y, x) => {
        sumX += x;
        sumY += y;
        sumXY += x * y;
        sumXX += x * x;
    });

    // Calculate slope and intercept
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    // Generate trend line points
    return data.map((_, i) => slope * i + intercept);
}

// Update Statistics Display
function updateStatistics(data) {
    const avgElement = document.getElementById('averageEvents');
    const maxElement = document.getElementById('maxEvents');
    const trendElement = document.getElementById('trendValue');
    const periodsElement = document.getElementById('totalPeriods');

    // Calculate statistics
    const average = data.counts.reduce((a, b) => a + b, 0) / data.counts.length;
    const max = Math.max(...data.counts);
    const trend = data.trend;
    
    // Update display
    avgElement.textContent = average.toFixed(1);
    maxElement.textContent = max;
    trendElement.textContent = `${(trend * 100).toFixed(1)}%`;
    trendElement.style.color = trend >= 0 ? '#28a745' : '#dc3545';
    periodsElement.textContent = data.counts.length;
}

// Show Error Message
function showError(message) {
    // Create error element if it doesn't exist
    let errorDiv = document.getElementById('errorMessage');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'errorMessage';
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 1000;
            display: none;
        `;
        document.body.appendChild(errorDiv);
    }

    // Show error message
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 3000);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize components
    initializeTrendsChart();
    await loadCategories();
    await updateTrendsData();

    // Add event listeners
    document.getElementById('categorySelect').addEventListener('change', updateTrendsData);

    // Period buttons
    document.querySelectorAll('.period-button').forEach(button => {
        button.addEventListener('click', async (e) => {
            // Update active button
            document.querySelectorAll('.period-button').forEach(btn => 
                btn.classList.remove('active'));
            e.target.classList.add('active');

            // Update period and refresh data
            currentPeriod = e.target.dataset.period;
            await updateTrendsData();
        });
    });
});
