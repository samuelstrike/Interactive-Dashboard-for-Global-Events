class EONETAnalysis {
    constructor() {
        this.charts = {};
        this.filters = {
            timePeriod: '7',  // Set the default time period to 7 days
            categories: [],
            region: 'all'
        };
        this.initialize();
    }

    async initialize() {
        try {
            await this.loadCategories();
            this.initializeCharts();
            this.setupEventListeners();
            await this.updateAnalysis();
        } catch (error) {
            this.showError('Initialization failed: ' + error.message);
        }
    }

    // Initialize Charts
    initializeCharts() {
        // Daily Events Chart
        this.charts.daily = new Chart(
            document.getElementById('dailyEventsChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Number of Events',
                    backgroundColor: '#FF6384',
                    borderColor: '#FF6384',
                    borderWidth: 1,
                    data: []
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Number of Events per Day (Last Week)',
                        font: { size: 16 }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        },
                        title: {
                            display: true,
                            text: 'Number of Events'
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 0,
                            minRotation: 0
                        }
                    }
                }
            }
        });

        // Geographic Distribution Chart
        this.charts.geographic = new Chart(
            document.getElementById('geographicChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56',
                        '#4BC0C0', '#9966FF', '#FF9F40'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Geographic Distribution'
                    }
                }
            }
        });

        // Event Categories Chart
        this.charts.categories = new Chart(
            document.getElementById('categoriesChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Events by Category',
                    backgroundColor: 'rgba(0, 123, 255, 0.5)',
                    data: []
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Event Distribution by Category'
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });

        // Severity Analysis Chart
        this.charts.severity = new Chart(
            document.getElementById('severityChart').getContext('2d'), {
            type: 'bubble',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Event Severity Analysis'
                    }
                },
                scales: {
                    x: { type: 'time', time: { unit: 'day' } },
                    y: { beginAtZero: true }
                }
            }
        });
    }

    // Data Loading Functions
    async loadCategories() {
        try {
            const response = await fetch('/api/categories');
            if (!response.ok) throw new Error('Failed to fetch categories');
            
            const data = await response.json();
            const select = document.getElementById('eventCategories');
            
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.title;
                select.appendChild(option);
            });
        } catch (error) {
            this.showError('Failed to load categories: ' + error.message);
        }
    }

    async updateAnalysis() {
        this.showLoading();
        try {
            // Fetch updated data
            const [dailyData, geoData, categoryData, severityData] = await Promise.all([
                this.fetchDailyData(),
                this.fetchGeographicData(),
                this.fetchCategoryData(),
                this.fetchSeverityData()
            ]);

            // Update charts
            this.updateDailyChart(dailyData);
            this.updateGeographicChart(geoData);
            this.updateCategoryChart(categoryData);
            this.updateSeverityChart(severityData);

            // Update insights
            this.updateInsights({
                daily: dailyData,
                geographic: geoData,
                categories: categoryData,
                severity: severityData
            });
        } catch (error) {
            this.showError('Failed to update analysis: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    // Chart Update Functions
    updateDailyChart(data) {
        this.charts.daily.data.labels = data.map(d => d.date);
        this.charts.daily.data.datasets[0].data = data.map(d => d.events);
        this.charts.daily.update();
    }

    updateGeographicChart(data) {
        this.charts.geographic.data.labels = Object.keys(data);
        this.charts.geographic.data.datasets[0].data = Object.values(data);
        this.charts.geographic.update();
    }

    updateCategoryChart(data) {
        this.charts.categories.data.labels = data.labels;
        this.charts.categories.data.datasets[0].data = data.values;
        this.charts.categories.update();
    }

    updateSeverityChart(data) {
        this.charts.severity.data.datasets = data.datasets;
        this.charts.severity.update();
    }

    // Data Fetching Functions
    async fetchDailyData() {
        const response = await fetch(`/api/analysis/daily?period=${this.filters.timePeriod}`);
        if (!response.ok) throw new Error('Failed to fetch daily data');
        return await response.json();
    }

    async fetchGeographicData() {
        const response = await fetch(`/api/analysis/geographic?region=${this.filters.region}`);
        if (!response.ok) throw new Error('Failed to fetch geographic data');
        return await response.json();
    }

    async fetchCategoryData() {
        const response = await fetch('/api/analysis/categories');
        if (!response.ok) throw new Error('Failed to fetch category data');
        return await response.json();
    }

    async fetchSeverityData() {
        const response = await fetch('/api/analysis/severity');
        if (!response.ok) throw new Error('Failed to fetch severity data');
        return await response.json();
    }

    // UI Helper Functions
    showLoading() {
        document.querySelector('.loading-overlay').style.display = 'flex';
    }

    hideLoading() {
        document.querySelector('.loading-overlay').style.display = 'none';
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    // Export Functions
    async exportData(format) {
        try {
            const response = await fetch('/api/analysis/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: format,
                    filters: this.filters
                })
            });

            if (!response.ok) throw new Error('Export failed');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `eonet-analysis.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            this.showError('Export failed: ' + error.message);
        }
    }

    // Event Listeners
    setupEventListeners() {
        // Time period selection
        document.getElementById('timePeriod').addEventListener('change', (e) => {
            this.filters.timePeriod = e.target.value;
            this.updateAnalysis();
        });

        // Category selection
        document.getElementById('eventCategories').addEventListener('change', (e) => {
            this.filters.categories = Array.from(e.target.selectedOptions).map(opt => opt.value);
            this.updateAnalysis();
        });

        // Region selection
        document.getElementById('region').addEventListener('change', (e) => {
            this.filters.region = e.target.value;
            this.updateAnalysis();
        });

        // Export buttons
        document.querySelectorAll('.export-buttons button').forEach(button => {
            button.addEventListener('click', (e) => {
                const format = e.target.dataset.format;
                this.exportData(format);
            });
        });
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.eonetAnalysis = new EONETAnalysis();
});
