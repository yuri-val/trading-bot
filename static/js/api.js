// API Client for Trading Bot
class TradingBotAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Network error' }));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error for ${endpoint}:`, error);
            throw error;
        }
    }

    // Health and Status
    async getHealth() {
        return this.request('/health');
    }

    async getSystemStatus() {
        return this.request('/api/v1/status');
    }

    async getConfig() {
        return this.request('/api/v1/config');
    }

    // Stock Analysis
    async getWatchlist() {
        return this.request('/api/v1/stocks/watchlist');
    }

    async getStockAnalysis(symbol) {
        return this.request(`/api/v1/stocks/${symbol}/analysis`);
    }

    async getStockRecommendation(symbol) {
        return this.request(`/api/v1/stocks/${symbol}/recommendation`);
    }

    async getStockHistory(symbol, days = 30) {
        return this.request(`/api/v1/stocks/${symbol}/history?days=${days}`);
    }

    async getStocksByCategory(category) {
        return this.request(`/api/v1/stocks/categories/${category}`);
    }

    async getTrendingStocks(limit = 10) {
        return this.request(`/api/v1/stocks/trending?limit=${limit}`);
    }

    // Reports
    async getCurrentRecommendations() {
        return this.request('/api/v1/reports/current-recommendations');
    }

    async getLatestDailyReport() {
        return this.request('/api/v1/reports/daily/latest');
    }

    async getDailyReport(date) {
        return this.request(`/api/v1/reports/daily/${date}`);
    }

    async generateSummaryReport(startDate, endDate) {
        return this.request('/api/v1/reports/summary', {
            method: 'POST',
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        });
    }

    async getSummaryReport(reportId) {
        return this.request(`/api/v1/reports/summary/${reportId}`);
    }

    async getLatestSummaryReport() {
        return this.request('/api/v1/reports/summary/latest');
    }

    async getReportsHistory(days = 30, reportType = 'DAILY') {
        return this.request(`/api/v1/reports/history?days=${days}&report_type=${reportType}`);
    }

    async getPerformanceSummary() {
        return this.request('/api/v1/reports/performance');
    }

    // AI Recommendations
    async getLatestAIRecommendations() {
        return this.request('/api/v1/reports/summary/latest/ai-recommendations');
    }
}

// Create global API instance
const api = new TradingBotAPI();

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatPercentage(value) {
    return `${(value * 100).toFixed(2)}%`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getConfidenceColor(confidence) {
    if (confidence >= 0.8) return '#28a745'; // Green
    if (confidence >= 0.6) return '#ffc107'; // Yellow
    return '#dc3545'; // Red
}

function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<i class="fas fa-hourglass"></i> Loading...';
        element.classList.add('loading');
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.remove('loading');
    }
}

function showError(message, elementId = null) {
    if (elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>${message}</span>
                </div>
            `;
            element.classList.remove('loading');
        }
    } else {
        // Show in modal
        document.getElementById('error-message').textContent = message;
        document.getElementById('error-modal').style.display = 'flex';
    }
}

// Error handling
window.addEventListener('unhandledrejection', event => {
    console.error('Unhandled promise rejection:', event.reason);
    showError('An unexpected error occurred. Please check the console for details.');
});