// Main Application Logic
class TradingBotApp {
    constructor() {
        this.currentTab = 'dashboard';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDashboard();
        this.checkSystemStatus();
        
        // Set default dates for report generation
        this.setDefaultDates();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Button event listeners
        document.getElementById('refresh-watchlist')?.addEventListener('click', () => this.loadWatchlist());
        document.getElementById('analyze-stock')?.addEventListener('click', () => this.analyzeStock());
        document.getElementById('load-latest-report')?.addEventListener('click', () => this.loadLatestReport());
        document.getElementById('load-performance')?.addEventListener('click', () => this.loadPerformance());
        document.getElementById('generate-summary')?.addEventListener('click', () => this.generateSummaryReport());

        // Enter key for stock analysis
        document.getElementById('stock-symbol')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.analyzeStock();
            }
        });

        // Modal close
        document.querySelector('.close-modal')?.addEventListener('click', () => {
            document.getElementById('error-modal').style.display = 'none';
        });

        // Click outside modal to close
        document.getElementById('error-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'error-modal') {
                e.target.style.display = 'none';
            }
        });
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        this.currentTab = tabName;

        // Load content for the active tab
        switch (tabName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'recommendations':
                this.loadRecommendations();
                break;
            case 'stocks':
                this.loadWatchlist();
                break;
            case 'reports':
                // Reports are loaded on demand
                break;
        }
    }

    async checkSystemStatus() {
        try {
            const health = await api.getHealth();
            const statusElement = document.getElementById('system-status');
            
            if (health.status === 'healthy') {
                statusElement.innerHTML = '<i class="fas fa-circle" style="color: #28a745;"></i> System Healthy';
                statusElement.className = 'status-indicator healthy';
            } else {
                statusElement.innerHTML = '<i class="fas fa-circle" style="color: #ffc107;"></i> System Degraded';
                statusElement.className = 'status-indicator warning';
            }
        } catch (error) {
            const statusElement = document.getElementById('system-status');
            statusElement.innerHTML = '<i class="fas fa-circle" style="color: #dc3545;"></i> System Error';
            statusElement.className = 'status-indicator error';
        }
    }

    async loadDashboard() {
        await Promise.all([
            this.loadSystemInfo(),
            this.loadTodaysPicks(),
            this.loadMarketOverview(),
            this.loadQuickStats()
        ]);
    }

    async loadSystemInfo() {
        showLoading('system-info');
        try {
            const status = await api.getSystemStatus();
            const config = await api.getConfig();
            
            document.getElementById('system-info').innerHTML = `
                <div class="info-grid">
                    <div class="info-item">
                        <i class="fas fa-server"></i>
                        <div>
                            <strong>API Status</strong>
                            <span>Operational</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-database"></i>
                        <div>
                            <strong>Storage</strong>
                            <span>${status.storage_status?.status || 'Unknown'}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-list"></i>
                        <div>
                            <strong>Tracked Stocks</strong>
                            <span>${status.api_configuration?.total_tracked_stocks || 0}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <i class="fas fa-dollar-sign"></i>
                        <div>
                            <strong>Monthly Budget</strong>
                            <span>${formatCurrency(config.investment_allocation?.total_monthly || 0)}</span>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            showError('Failed to load system information', 'system-info');
        }
    }

    async loadTodaysPicks() {
        showLoading('todays-picks');
        try {
            const recommendations = await api.getCurrentRecommendations();
            
            document.getElementById('todays-picks').innerHTML = `
                <div class="recommendations">
                    <div class="recommendation stable">
                        <div class="rec-header">
                            <i class="fas fa-shield-alt"></i>
                            <span>Stable Pick</span>
                        </div>
                        <div class="rec-symbol">${recommendations.stable_recommendation?.symbol || 'N/A'}</div>
                        <div class="rec-amount">${formatCurrency(recommendations.stable_recommendation?.allocation || 0)}</div>
                        <div class="rec-confidence" style="color: ${getConfidenceColor(recommendations.stable_recommendation?.confidence || 0)}">
                            Confidence: ${formatPercentage(recommendations.stable_recommendation?.confidence || 0)}
                        </div>
                    </div>
                    <div class="recommendation risky">
                        <div class="rec-header">
                            <i class="fas fa-rocket"></i>
                            <span>Risky Pick</span>
                        </div>
                        <div class="rec-symbol">${recommendations.risky_recommendation?.symbol || 'N/A'}</div>
                        <div class="rec-amount">${formatCurrency(recommendations.risky_recommendation?.allocation || 0)}</div>
                        <div class="rec-confidence" style="color: ${getConfidenceColor(recommendations.risky_recommendation?.confidence || 0)}">
                            Confidence: ${formatPercentage(recommendations.risky_recommendation?.confidence || 0)}
                        </div>
                    </div>
                </div>
                <div class="rec-date">
                    <i class="fas fa-calendar"></i>
                    ${formatDate(recommendations.date)}
                </div>
            `;
        } catch (error) {
            showError('Failed to load today\'s recommendations', 'todays-picks');
        }
    }

    async loadMarketOverview() {
        showLoading('market-overview');
        try {
            const report = await api.getLatestDailyReport();
            const marketData = report.report?.market_overview;
            
            if (marketData) {
                document.getElementById('market-overview').innerHTML = `
                    <div class="market-info">
                        <div class="market-sentiment ${marketData.market_sentiment?.toLowerCase() || 'neutral'}">
                            <i class="fas fa-chart-line"></i>
                            <span>Market Sentiment: ${marketData.market_sentiment || 'Unknown'}</span>
                        </div>
                        <div class="market-themes">
                            <strong>Key Themes:</strong>
                            <ul>
                                ${(marketData.market_themes || []).map(theme => `<li>${theme}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                `;
            } else {
                document.getElementById('market-overview').innerHTML = `
                    <div class="no-data">
                        <i class="fas fa-info-circle"></i>
                        <span>No recent market data available</span>
                    </div>
                `;
            }
        } catch (error) {
            showError('Failed to load market overview', 'market-overview');
        }
    }

    async loadQuickStats() {
        showLoading('quick-stats');
        try {
            const performance = await api.getPerformanceSummary();
            
            document.getElementById('quick-stats').innerHTML = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <i class="fas fa-chart-bar"></i>
                        <div>
                            <strong>${performance.total_reports || 0}</strong>
                            <span>Reports (30d)</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-bullseye"></i>
                        <div>
                            <strong>${formatPercentage(performance.average_confidence || 0)}</strong>
                            <span>Avg Confidence</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-check-circle"></i>
                        <div>
                            <strong>${Math.round(performance.system_reliability || 0)}%</strong>
                            <span>Reliability</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-crown"></i>
                        <div>
                            <strong>${performance.most_recommended?.stable?.[0]?.[0] || 'N/A'}</strong>
                            <span>Top Stable</span>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            showError('Failed to load statistics', 'quick-stats');
        }
    }

    async loadRecommendations() {
        showLoading('current-recommendations');
        try {
            const recommendations = await api.getCurrentRecommendations();
            
            document.getElementById('current-recommendations').innerHTML = `
                <div class="detailed-recommendations">
                    <div class="rec-card stable-card">
                        <div class="rec-card-header">
                            <i class="fas fa-shield-alt"></i>
                            <h3>Stable Investment</h3>
                        </div>
                        <div class="rec-card-body">
                            <div class="rec-symbol-large">${recommendations.stable_recommendation?.symbol || 'N/A'}</div>
                            <div class="rec-allocation">${formatCurrency(recommendations.stable_recommendation?.allocation || 0)}</div>
                            <div class="rec-confidence-bar">
                                <span>Confidence: ${formatPercentage(recommendations.stable_recommendation?.confidence || 0)}</span>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: ${(recommendations.stable_recommendation?.confidence || 0) * 100}%; background-color: ${getConfidenceColor(recommendations.stable_recommendation?.confidence || 0)}"></div>
                                </div>
                            </div>
                            <div class="rec-reasoning">
                                <strong>Reasoning:</strong>
                                <p>${recommendations.stable_recommendation?.reasoning || 'No reasoning available'}</p>
                            </div>
                            ${recommendations.stable_recommendation?.expected_return_30d ? `
                                <div class="expected-return">
                                    <strong>Expected 30d Return:</strong> ${formatPercentage(recommendations.stable_recommendation.expected_return_30d)}
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    <div class="rec-card risky-card">
                        <div class="rec-card-header">
                            <i class="fas fa-rocket"></i>
                            <h3>Risky Investment</h3>
                        </div>
                        <div class="rec-card-body">
                            <div class="rec-symbol-large">${recommendations.risky_recommendation?.symbol || 'N/A'}</div>
                            <div class="rec-allocation">${formatCurrency(recommendations.risky_recommendation?.allocation || 0)}</div>
                            <div class="rec-confidence-bar">
                                <span>Confidence: ${formatPercentage(recommendations.risky_recommendation?.confidence || 0)}</span>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: ${(recommendations.risky_recommendation?.confidence || 0) * 100}%; background-color: ${getConfidenceColor(recommendations.risky_recommendation?.confidence || 0)}"></div>
                                </div>
                            </div>
                            <div class="rec-reasoning">
                                <strong>Reasoning:</strong>
                                <p>${recommendations.risky_recommendation?.reasoning || 'No reasoning available'}</p>
                            </div>
                            ${recommendations.risky_recommendation?.expected_return_30d ? `
                                <div class="expected-return">
                                    <strong>Expected 30d Return:</strong> ${formatPercentage(recommendations.risky_recommendation.expected_return_30d)}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>

                <div class="market-context">
                    <h4><i class="fas fa-globe"></i> Market Context</h4>
                    <p>${recommendations.market_context || 'No market context available'}</p>
                </div>

                <div class="rec-timestamp">
                    <i class="fas fa-clock"></i>
                    Generated: ${formatDate(recommendations.date)}
                </div>
            `;
        } catch (error) {
            showError('Failed to load recommendations', 'current-recommendations');
        }
    }

    async loadWatchlist() {
        showLoading('stable-stocks');
        showLoading('risky-stocks');
        
        try {
            const watchlist = await api.getWatchlist();
            
            // Load stable stocks
            const stableStocks = watchlist.stable || [];
            document.getElementById('stable-stocks').innerHTML = `
                <div class="stock-list">
                    ${stableStocks.map(symbol => `
                        <div class="stock-item" data-symbol="${symbol}">
                            <span class="stock-symbol">${symbol}</span>
                            <button class="btn btn-sm" onclick="app.analyzeStockQuick('${symbol}')">
                                <i class="fas fa-chart-line"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>
                <div class="stock-count">${stableStocks.length} stocks</div>
            `;

            // Load risky stocks
            const riskyStocks = watchlist.risky || [];
            document.getElementById('risky-stocks').innerHTML = `
                <div class="stock-list">
                    ${riskyStocks.map(symbol => `
                        <div class="stock-item" data-symbol="${symbol}">
                            <span class="stock-symbol">${symbol}</span>
                            <button class="btn btn-sm" onclick="app.analyzeStockQuick('${symbol}')">
                                <i class="fas fa-chart-line"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>
                <div class="stock-count">${riskyStocks.length} stocks</div>
            `;

        } catch (error) {
            showError('Failed to load watchlist', 'stable-stocks');
            showError('Failed to load watchlist', 'risky-stocks');
        }
    }

    async analyzeStock() {
        const symbol = document.getElementById('stock-symbol').value.trim().toUpperCase();
        if (!symbol) {
            showError('Please enter a stock symbol');
            return;
        }

        this.analyzeStockQuick(symbol);
    }

    async analyzeStockQuick(symbol) {
        const resultDiv = document.getElementById('stock-analysis-result');
        resultDiv.innerHTML = '<i class="fas fa-search"></i> Analyzing ' + symbol + '...';
        
        try {
            const [analysis, recommendation] = await Promise.all([
                api.getStockAnalysis(symbol),
                api.getStockRecommendation(symbol)
            ]);

            resultDiv.innerHTML = `
                <div class="analysis-result">
                    <div class="analysis-header">
                        <h3>${symbol} Analysis</h3>
                        <span class="analysis-timestamp">${formatDate(analysis.timestamp || new Date())}</span>
                    </div>
                    
                    <div class="analysis-grid">
                        <div class="analysis-card">
                            <h4>Current Price</h4>
                            <div class="price-info">
                                <span class="current-price">${formatCurrency(analysis.current_price || 0)}</span>
                                ${analysis.price_change ? `
                                    <span class="price-change ${analysis.price_change >= 0 ? 'positive' : 'negative'}">
                                        ${analysis.price_change >= 0 ? '+' : ''}${formatPercentage(analysis.price_change)}
                                    </span>
                                ` : ''}
                            </div>
                        </div>
                        
                        <div class="analysis-card">
                            <h4>Recommendation</h4>
                            <div class="recommendation-info">
                                <span class="recommendation-action">${recommendation.recommendation || 'N/A'}</span>
                                <span class="confidence" style="color: ${getConfidenceColor(recommendation.confidence || 0)}">
                                    ${formatPercentage(recommendation.confidence || 0)} confidence
                                </span>
                            </div>
                        </div>
                    </div>

                    ${recommendation.reasoning ? `
                        <div class="reasoning-section">
                            <h4>Analysis Reasoning</h4>
                            <p>${recommendation.reasoning}</p>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (error) {
            resultDiv.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Failed to analyze ${symbol}: ${error.message}</span>
                </div>
            `;
        }
    }

    async loadLatestReport() {
        showLoading('latest-report');
        try {
            const reportData = await api.getLatestDailyReport();
            const report = reportData.report;
            
            document.getElementById('latest-report').innerHTML = `
                <div class="report-content">
                    <div class="report-header">
                        <h4>Daily Report - ${formatDate(report.date)}</h4>
                    </div>
                    
                    <div class="report-summary">
                        <div class="summary-item">
                            <strong>Analyzed Stocks:</strong> ${report.analyzed_stocks_count || 0}
                        </div>
                        <div class="summary-item">
                            <strong>Processing Time:</strong> ${report.processing_time_minutes || 0} minutes
                        </div>
                        <div class="summary-item">
                            <strong>Data Quality:</strong> ${formatPercentage(report.data_quality_score || 0)}
                        </div>
                    </div>

                    ${report.market_risks ? `
                        <div class="risks-section">
                            <h5>Market Risks</h5>
                            <ul>
                                ${report.market_risks.map(risk => `<li>${risk}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (error) {
            showError('Failed to load latest report', 'latest-report');
        }
    }

    async loadPerformance() {
        showLoading('performance-summary');
        try {
            const performance = await api.getPerformanceSummary();
            
            document.getElementById('performance-summary').innerHTML = `
                <div class="performance-content">
                    <div class="performance-overview">
                        <h4>30-Day Performance Overview</h4>
                        <div class="perf-stats">
                            <div class="perf-stat">
                                <strong>${performance.total_reports || 0}</strong>
                                <span>Total Reports</span>
                            </div>
                            <div class="perf-stat">
                                <strong>${formatPercentage(performance.average_confidence || 0)}</strong>
                                <span>Average Confidence</span>
                            </div>
                            <div class="perf-stat">
                                <strong>${Math.round(performance.system_reliability || 0)}%</strong>
                                <span>System Reliability</span>
                            </div>
                        </div>
                    </div>

                    <div class="top-performers">
                        <div class="performer-section">
                            <h5>Top Stable Performers</h5>
                            <div class="performer-list">
                                ${(performance.most_recommended?.stable || []).map(([symbol, count]) => `
                                    <div class="performer-item">
                                        <span class="symbol">${symbol}</span>
                                        <span class="count">${count} times</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <div class="performer-section">
                            <h5>Top Risky Performers</h5>
                            <div class="performer-list">
                                ${(performance.most_recommended?.risky || []).map(([symbol, count]) => `
                                    <div class="performer-item">
                                        <span class="symbol">${symbol}</span>
                                        <span class="count">${count} times</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            showError('Failed to load performance data', 'performance-summary');
        }
    }

    async generateSummaryReport() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        
        if (!startDate || !endDate) {
            showError('Please select both start and end dates');
            return;
        }

        showLoading('summary-report');
        try {
            const result = await api.generateSummaryReport(startDate, endDate);
            
            document.getElementById('summary-report').innerHTML = `
                <div class="summary-report-content">
                    <div class="report-header">
                        <h4>Summary Report Generated</h4>
                        <span class="report-id">ID: ${result.report_id}</span>
                    </div>
                    
                    <div class="report-details">
                        <pre>${JSON.stringify(result.report, null, 2)}</pre>
                    </div>
                </div>
            `;
        } catch (error) {
            showError('Failed to generate summary report', 'summary-report');
        }
    }

    setDefaultDates() {
        const today = new Date();
        const monthAgo = new Date(today);
        monthAgo.setDate(today.getDate() - 30);
        
        document.getElementById('end-date').value = today.toISOString().split('T')[0];
        document.getElementById('start-date').value = monthAgo.toISOString().split('T')[0];
    }
}

// Initialize the app when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new TradingBotApp();
});