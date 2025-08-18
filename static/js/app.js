// Main Application Logic
// Supports hashtag navigation: #dashboard, #recommendations, #ai-recommendations, #stocks, #reports
class TradingBotApp {
    constructor() {
        this.currentTab = 'dashboard';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupHashNavigation();
        this.loadInitialTab();
        this.checkSystemStatus();
        
        // Set default dates for report generation
        this.setDefaultDates();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = e.target.dataset.tab || e.target.closest('.tab-button').dataset.tab;
                this.switchTab(tabName); // Will update hash by default
            });
        });

        // Button event listeners
        document.getElementById('refresh-watchlist')?.addEventListener('click', () => this.loadWatchlist());
        document.getElementById('refresh-ai-recommendations')?.addEventListener('click', () => this.loadAIRecommendations());
        document.getElementById('analyze-stock')?.addEventListener('click', () => this.analyzeStock());
        document.getElementById('load-latest-report')?.addEventListener('click', () => this.loadLatestReport());
        document.getElementById('load-performance')?.addEventListener('click', () => this.loadPerformance());
        document.getElementById('load-latest-summary')?.addEventListener('click', () => this.loadLatestSummaryReport());
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

    setupHashNavigation() {
        // Listen for hash changes (back/forward navigation)
        window.addEventListener('hashchange', () => {
            this.loadTabFromHash();
        });
    }

    loadInitialTab() {
        // Load tab based on current URL hash or default to dashboard
        const hash = window.location.hash.substring(1); // Remove # symbol
        const validTabs = ['dashboard', 'recommendations', 'ai-recommendations', 'stocks', 'reports'];
        
        if (hash && validTabs.includes(hash)) {
            this.switchTab(hash, false); // false = don't update URL hash again
        } else {
            this.switchTab('dashboard', false);
            // Set default hash if no valid hash exists
            if (!hash || !validTabs.includes(hash)) {
                window.history.replaceState(null, null, '#dashboard');
            }
        }
    }

    loadTabFromHash() {
        const hash = window.location.hash.substring(1);
        const validTabs = ['dashboard', 'recommendations', 'ai-recommendations', 'stocks', 'reports'];
        
        if (hash && validTabs.includes(hash) && hash !== this.currentTab) {
            this.switchTab(hash, false); // false = don't update URL hash again
        }
    }

    switchTab(tabName, updateHash = true) {
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

        // Update URL hash if requested
        if (updateHash) {
            window.history.pushState(null, null, `#${tabName}`);
        }

        // Load content for the active tab
        switch (tabName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'recommendations':
                this.loadRecommendations();
                break;
            case 'ai-recommendations':
                this.loadAIRecommendations();
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
            this.loadAIPicksSummary(),
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

    async loadAIPicksSummary() {
        showLoading('ai-picks-summary');
        try {
            const aiRecs = await api.getLatestAIRecommendations();
            
            const stableSymbol = aiRecs.ai_stable_recommendation?.symbol || 'N/A';
            const riskySymbol = aiRecs.ai_risky_recommendation?.symbol || 'N/A';
            const totalAllocation = (aiRecs.ai_stable_recommendation?.allocation || 0) + (aiRecs.ai_risky_recommendation?.allocation || 0);
            const avgConfidence = ((aiRecs.ai_stable_recommendation?.confidence || 0) + (aiRecs.ai_risky_recommendation?.confidence || 0)) / 2;
            
            document.getElementById('ai-picks-summary').innerHTML = `
                <div class="ai-summary">
                    <div class="ai-summary-header">
                        <div class="ai-picks-overview">
                            <span class="summary-symbols">${stableSymbol} • ${riskySymbol}</span>
                            <span class="summary-total">${formatCurrency(totalAllocation)} total</span>
                        </div>
                    </div>
                    <div class="ai-summary-metrics">
                        <div class="metric">
                            <i class="fas fa-brain"></i>
                            <span>AI Confidence: ${formatPercentage(avgConfidence)}</span>
                        </div>
                        <div class="metric">
                            <i class="fas fa-calendar"></i>
                            <span>Analysis: ${aiRecs.days_analyzed || 0} days</span>
                        </div>
                    </div>
                    <div class="ai-summary-breakdown">
                        <div class="breakdown-item stable">
                            <span class="category">Stable:</span>
                            <span class="amount">${formatCurrency(aiRecs.ai_stable_recommendation?.allocation || 0)}</span>
                        </div>
                        <div class="breakdown-item risky">
                            <span class="category">Growth:</span>
                            <span class="amount">${formatCurrency(aiRecs.ai_risky_recommendation?.allocation || 0)}</span>
                        </div>
                    </div>
                </div>
                <div class="ai-summary-footer">
                    <i class="fas fa-info-circle"></i>
                    <span>Based on comprehensive AI analysis</span>
                </div>
            `;
        } catch (error) {
            document.getElementById('ai-picks-summary').innerHTML = `
                <div class="ai-summary-empty">
                    <i class="fas fa-robot"></i>
                    <p>No AI analysis available</p>
                    <small>AI picks will appear after summary report generation</small>
                </div>
            `;
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

    async loadAIRecommendations() {
        showLoading('ai-recommendations-content');
        try {
            const aiRecs = await api.getLatestAIRecommendations();
            
            document.getElementById('ai-recommendations-content').innerHTML = `
                <div class="ai-recommendations-wrapper">
                    <!-- Report Info Header -->
                    <div class="ai-report-header">
                        <div class="report-info">
                            <div class="report-meta">
                                <span class="report-id">${aiRecs.report_id}</span>
                                <span class="analysis-period">${aiRecs.days_analyzed} days analyzed</span>
                            </div>
                            <div class="generated-date">
                                <i class="fas fa-calendar-alt"></i>
                                Generated: ${formatDate(aiRecs.generated_at)}
                            </div>
                        </div>
                    </div>

                    <!-- AI Recommendations Grid -->
                    <div class="ai-recommendations-grid">
                        <!-- Stable AI Recommendation -->
                        ${aiRecs.ai_stable_recommendation ? `
                            <div class="ai-rec-card stable-ai-card">
                                <div class="ai-rec-header">
                                    <div class="rec-icon-wrapper">
                                        <i class="fas fa-shield-alt"></i>
                                        <span class="ai-badge">AI</span>
                                    </div>
                                    <div class="rec-category">
                                        <h3>Stable Investment Pick</h3>
                                        <p>Conservative growth strategy</p>
                                    </div>
                                    <div class="rec-allocation-large">
                                        <div class="allocation-amount">${formatCurrency(aiRecs.ai_stable_recommendation.allocation)}</div>
                                        <div class="allocation-label">Recommended Investment</div>
                                    </div>
                                </div>

                                <div class="ai-rec-body">
                                    <!-- Stock Symbol and Price -->
                                    <div class="stock-info-section">
                                        <div class="stock-symbol-xl">${aiRecs.ai_stable_recommendation.symbol}</div>
                                        ${aiRecs.ai_stable_recommendation.current_price ? `
                                            <div class="price-info">
                                                <div class="current-price">$${aiRecs.ai_stable_recommendation.current_price.toFixed(2)}</div>
                                                ${aiRecs.ai_stable_recommendation.target_price ? `
                                                    <div class="price-targets">
                                                        <span class="target-price">Target: $${aiRecs.ai_stable_recommendation.target_price.toFixed(2)}</span>
                                                        ${aiRecs.ai_stable_recommendation.expected_return ? `
                                                            <span class="expected-return">(${formatPercentage(aiRecs.ai_stable_recommendation.expected_return)} return)</span>
                                                        ` : ''}
                                                    </div>
                                                ` : ''}
                                            </div>
                                        ` : ''}
                                    </div>

                                    <!-- Confidence and Sentiment -->
                                    <div class="metrics-section">
                                        <div class="confidence-section">
                                            <div class="metric-label">AI Confidence</div>
                                            <div class="confidence-bar-large">
                                                <div class="confidence-fill" style="width: ${aiRecs.ai_stable_recommendation.confidence * 100}%; background-color: ${getConfidenceColor(aiRecs.ai_stable_recommendation.confidence)}"></div>
                                                <span class="confidence-text">${formatPercentage(aiRecs.ai_stable_recommendation.confidence)}</span>
                                            </div>
                                        </div>

                                        ${aiRecs.ai_stable_recommendation.news_sentiment ? `
                                            <div class="sentiment-section">
                                                <div class="metric-label">News Sentiment</div>
                                                <div class="sentiment-indicator sentiment-${aiRecs.ai_stable_recommendation.news_sentiment.toLowerCase()}">
                                                    <i class="fas fa-${aiRecs.ai_stable_recommendation.news_sentiment === 'POSITIVE' ? 'thumbs-up' : aiRecs.ai_stable_recommendation.news_sentiment === 'NEGATIVE' ? 'thumbs-down' : 'minus'}"></i>
                                                    <span>${aiRecs.ai_stable_recommendation.news_sentiment}</span>
                                                </div>
                                            </div>
                                        ` : ''}
                                    </div>

                                    <!-- AI Reasoning -->
                                    <div class="reasoning-section">
                                        <h4><i class="fas fa-brain"></i> AI Analysis</h4>
                                        <div class="reasoning-text">
                                            <p>${aiRecs.ai_stable_recommendation.reasoning}</p>
                                        </div>
                                    </div>

                                    <!-- Key Metrics -->
                                    ${aiRecs.ai_stable_recommendation.key_metrics && Object.keys(aiRecs.ai_stable_recommendation.key_metrics).length > 0 ? `
                                        <div class="key-metrics-section">
                                            <h5>Key Financial Metrics</h5>
                                            <div class="metrics-grid">
                                                ${Object.entries(aiRecs.ai_stable_recommendation.key_metrics).map(([key, value]) => `
                                                    <div class="metric-item">
                                                        <span class="metric-label">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                                                        <span class="metric-value">${typeof value === 'number' ? (key.includes('ratio') || key.includes('beta') ? value.toFixed(2) : value.toLocaleString()) : value || 'N/A'}</span>
                                                    </div>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}

                                    <!-- Risk Factors -->
                                    ${aiRecs.ai_stable_recommendation.risk_factors && aiRecs.ai_stable_recommendation.risk_factors.length > 0 ? `
                                        <div class="risk-factors-section">
                                            <h5><i class="fas fa-exclamation-triangle"></i> Risk Factors</h5>
                                            <ul class="risk-factors-list">
                                                ${aiRecs.ai_stable_recommendation.risk_factors.map(risk => `<li>${risk}</li>`).join('')}
                                            </ul>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        ` : '<div class="no-ai-rec">No AI stable recommendation available</div>'}

                        <!-- Risky AI Recommendation -->
                        ${aiRecs.ai_risky_recommendation ? `
                            <div class="ai-rec-card risky-ai-card">
                                <div class="ai-rec-header">
                                    <div class="rec-icon-wrapper">
                                        <i class="fas fa-rocket"></i>
                                        <span class="ai-badge">AI</span>
                                    </div>
                                    <div class="rec-category">
                                        <h3>Growth Investment Pick</h3>
                                        <p>High potential growth opportunity</p>
                                    </div>
                                    <div class="rec-allocation-large">
                                        <div class="allocation-amount">${formatCurrency(aiRecs.ai_risky_recommendation.allocation)}</div>
                                        <div class="allocation-label">Recommended Investment</div>
                                    </div>
                                </div>

                                <div class="ai-rec-body">
                                    <!-- Stock Symbol and Price -->
                                    <div class="stock-info-section">
                                        <div class="stock-symbol-xl">${aiRecs.ai_risky_recommendation.symbol}</div>
                                        ${aiRecs.ai_risky_recommendation.current_price ? `
                                            <div class="price-info">
                                                <div class="current-price">$${aiRecs.ai_risky_recommendation.current_price.toFixed(2)}</div>
                                                ${aiRecs.ai_risky_recommendation.target_price ? `
                                                    <div class="price-targets">
                                                        <span class="target-price">Target: $${aiRecs.ai_risky_recommendation.target_price.toFixed(2)}</span>
                                                        ${aiRecs.ai_risky_recommendation.expected_return ? `
                                                            <span class="expected-return">(${formatPercentage(aiRecs.ai_risky_recommendation.expected_return)} return)</span>
                                                        ` : ''}
                                                    </div>
                                                ` : ''}
                                            </div>
                                        ` : ''}
                                    </div>

                                    <!-- Confidence and Sentiment -->
                                    <div class="metrics-section">
                                        <div class="confidence-section">
                                            <div class="metric-label">AI Confidence</div>
                                            <div class="confidence-bar-large">
                                                <div class="confidence-fill" style="width: ${aiRecs.ai_risky_recommendation.confidence * 100}%; background-color: ${getConfidenceColor(aiRecs.ai_risky_recommendation.confidence)}"></div>
                                                <span class="confidence-text">${formatPercentage(aiRecs.ai_risky_recommendation.confidence)}</span>
                                            </div>
                                        </div>

                                        ${aiRecs.ai_risky_recommendation.news_sentiment ? `
                                            <div class="sentiment-section">
                                                <div class="metric-label">News Sentiment</div>
                                                <div class="sentiment-indicator sentiment-${aiRecs.ai_risky_recommendation.news_sentiment.toLowerCase()}">
                                                    <i class="fas fa-${aiRecs.ai_risky_recommendation.news_sentiment === 'POSITIVE' ? 'thumbs-up' : aiRecs.ai_risky_recommendation.news_sentiment === 'NEGATIVE' ? 'thumbs-down' : 'minus'}"></i>
                                                    <span>${aiRecs.ai_risky_recommendation.news_sentiment}</span>
                                                </div>
                                            </div>
                                        ` : ''}
                                    </div>

                                    <!-- AI Reasoning -->
                                    <div class="reasoning-section">
                                        <h4><i class="fas fa-brain"></i> AI Analysis</h4>
                                        <div class="reasoning-text">
                                            <p>${aiRecs.ai_risky_recommendation.reasoning}</p>
                                        </div>
                                    </div>

                                    <!-- Key Metrics -->
                                    ${aiRecs.ai_risky_recommendation.key_metrics && Object.keys(aiRecs.ai_risky_recommendation.key_metrics).length > 0 ? `
                                        <div class="key-metrics-section">
                                            <h5>Key Financial Metrics</h5>
                                            <div class="metrics-grid">
                                                ${Object.entries(aiRecs.ai_risky_recommendation.key_metrics).map(([key, value]) => `
                                                    <div class="metric-item">
                                                        <span class="metric-label">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                                                        <span class="metric-value">${typeof value === 'number' ? (key.includes('ratio') || key.includes('beta') ? value.toFixed(2) : value.toLocaleString()) : value || 'N/A'}</span>
                                                    </div>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}

                                    <!-- Risk Factors -->
                                    ${aiRecs.ai_risky_recommendation.risk_factors && aiRecs.ai_risky_recommendation.risk_factors.length > 0 ? `
                                        <div class="risk-factors-section">
                                            <h5><i class="fas fa-exclamation-triangle"></i> Risk Factors</h5>
                                            <ul class="risk-factors-list">
                                                ${aiRecs.ai_risky_recommendation.risk_factors.map(risk => `<li>${risk}</li>`).join('')}
                                            </ul>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        ` : '<div class="no-ai-rec">No AI risky recommendation available</div>'}
                    </div>

                    <!-- Investment Summary -->
                    <div class="investment-summary">
                        <div class="summary-header">
                            <h3><i class="fas fa-calculator"></i> Investment Summary</h3>
                        </div>
                        <div class="summary-content">
                            <div class="total-allocation">
                                <div class="total-amount">
                                    ${formatCurrency((aiRecs.ai_stable_recommendation?.allocation || 0) + (aiRecs.ai_risky_recommendation?.allocation || 0))}
                                </div>
                                <div class="total-label">Total Recommended Investment</div>
                            </div>
                            <div class="allocation-breakdown">
                                <div class="breakdown-item">
                                    <span class="category">Stable:</span>
                                    <span class="amount">${formatCurrency(aiRecs.ai_stable_recommendation?.allocation || 0)}</span>
                                    <span class="percentage">(${Math.round(((aiRecs.ai_stable_recommendation?.allocation || 0) / ((aiRecs.ai_stable_recommendation?.allocation || 0) + (aiRecs.ai_risky_recommendation?.allocation || 0)) * 100) || 0)}%)</span>
                                </div>
                                <div class="breakdown-item">
                                    <span class="category">Growth:</span>
                                    <span class="amount">${formatCurrency(aiRecs.ai_risky_recommendation?.allocation || 0)}</span>
                                    <span class="percentage">(${Math.round(((aiRecs.ai_risky_recommendation?.allocation || 0) / ((aiRecs.ai_stable_recommendation?.allocation || 0) + (aiRecs.ai_risky_recommendation?.allocation || 0)) * 100) || 0)}%)</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Data Timestamp -->
                    <div class="data-timestamp">
                        <i class="fas fa-clock"></i>
                        <span>Data retrieved: ${formatDate(aiRecs.retrieved_at)}</span>
                    </div>
                </div>
            `;
        } catch (error) {
            showError('Failed to load AI recommendations. Make sure you have generated a summary report with AI analysis.', 'ai-recommendations-content');
        }
    }

    async loadWatchlist() {
        showLoading('stable-stocks');
        showLoading('risky-stocks');
        
        try {
            const watchlist = await api.getWatchlist();
            console.log('Watchlist response:', watchlist); // Debug log
            
            // Load stable stocks - handle multiple possible API response structures
            const stableStocks = watchlist.stable_stocks?.symbols || watchlist.stable || [];
            if (stableStocks.length > 0) {
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
            } else {
                document.getElementById('stable-stocks').innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-info-circle"></i>
                        <p>No stable stocks available</p>
                        <small>Stocks will appear here after daily analysis</small>
                    </div>
                `;
            }

            // Load risky stocks - handle multiple possible API response structures
            const riskyStocks = watchlist.risky_stocks?.symbols || watchlist.risky || [];
            if (riskyStocks.length > 0) {
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
            } else {
                document.getElementById('risky-stocks').innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-info-circle"></i>
                        <p>No risky stocks available</p>
                        <small>Stocks will appear here after daily analysis</small>
                    </div>
                `;
            }

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
            const analysis = await api.getStockAnalysis(symbol);
            const stockData = analysis.data;
            
            resultDiv.innerHTML = `
                <div class="detailed-analysis">
                    <div class="analysis-header">
                        <div class="stock-title">
                            <h3>${stockData.symbol}</h3>
                            <span class="category-badge ${stockData.category.toLowerCase()}">${stockData.category}</span>
                        </div>
                        <div class="last-updated">
                            Last Updated: ${formatDate(stockData.date)}
                        </div>
                    </div>

                    <!-- Price Information Section -->
                    <div class="section price-section">
                        <h4><i class="fas fa-dollar-sign"></i> Price Information</h4>
                        <div class="price-grid">
                            <div class="price-card main-price">
                                <div class="price-label">Current Price</div>
                                <div class="price-value">${formatCurrency(stockData.price_data.close)}</div>
                                <div class="price-change ${stockData.price_data.change_percent >= 0 ? 'positive' : 'negative'}">
                                    ${stockData.price_data.change_percent >= 0 ? '+' : ''}${stockData.price_data.change_percent.toFixed(2)}%
                                    (${formatCurrency(stockData.price_data.close - stockData.price_data.previous_close)})
                                </div>
                            </div>
                            <div class="price-details">
                                <div class="price-item">
                                    <span class="label">Open:</span>
                                    <span class="value">${formatCurrency(stockData.price_data.open)}</span>
                                </div>
                                <div class="price-item">
                                    <span class="label">High:</span>
                                    <span class="value">${formatCurrency(stockData.price_data.high)}</span>
                                </div>
                                <div class="price-item">
                                    <span class="label">Low:</span>
                                    <span class="value">${formatCurrency(stockData.price_data.low)}</span>
                                </div>
                                <div class="price-item">
                                    <span class="label">Previous Close:</span>
                                    <span class="value">${formatCurrency(stockData.price_data.previous_close)}</span>
                                </div>
                                <div class="price-item">
                                    <span class="label">Volume:</span>
                                    <span class="value">${stockData.price_data.volume.toLocaleString()}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- AI Analysis Section -->
                    ${stockData.ai_analysis ? `
                        <div class="section ai-analysis-section">
                            <h4><i class="fas fa-robot"></i> AI Analysis</h4>
                            <div class="ai-analysis-grid">
                                <div class="analysis-card">
                                    <div class="card-header">
                                        <h5>Recommendation</h5>
                                        <span class="recommendation-badge ${stockData.ai_analysis.recommendation.toLowerCase()}">${stockData.ai_analysis.recommendation}</span>
                                    </div>
                                    <div class="card-content">
                                        <div class="confidence-bar">
                                            <span>Confidence: ${formatPercentage(stockData.ai_analysis.confidence_level)}</span>
                                            <div class="progress-bar">
                                                <div class="progress-fill" style="width: ${stockData.ai_analysis.confidence_level * 100}%; background-color: ${getConfidenceColor(stockData.ai_analysis.confidence_level)}"></div>
                                            </div>
                                        </div>
                                        <div class="risk-score">
                                            <span>Risk Score: ${formatPercentage(stockData.ai_analysis.risk_score)}</span>
                                        </div>
                                    </div>
                                </div>

                                <div class="analysis-card">
                                    <div class="card-header">
                                        <h5>Technical Analysis</h5>
                                    </div>
                                    <div class="card-content">
                                        <div class="tech-item">
                                            <span class="tech-label">Trend Direction:</span>
                                            <span class="trend-badge ${stockData.ai_analysis.trend_direction.toLowerCase()}">${stockData.ai_analysis.trend_direction}</span>
                                        </div>
                                        <div class="tech-item">
                                            <span class="tech-label">Trend Strength:</span>
                                            <span class="trend-strength">${(stockData.ai_analysis.trend_strength * 100).toFixed(1)}%</span>
                                        </div>
                                        ${stockData.ai_analysis.support_level ? `
                                            <div class="tech-item">
                                                <span class="tech-label">Support:</span>
                                                <span class="support-level">${formatCurrency(stockData.ai_analysis.support_level)}</span>
                                            </div>
                                        ` : ''}
                                        ${stockData.ai_analysis.resistance_level ? `
                                            <div class="tech-item">
                                                <span class="tech-label">Resistance:</span>
                                                <span class="resistance-level">${formatCurrency(stockData.ai_analysis.resistance_level)}</span>
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>

                            ${stockData.ai_analysis.key_factors && stockData.ai_analysis.key_factors.length > 0 ? `
                                <div class="key-factors">
                                    <h5>Key Factors</h5>
                                    <ul class="factors-list">
                                        ${stockData.ai_analysis.key_factors.map(factor => `<li>${factor}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}

                            ${stockData.ai_analysis.reasoning ? `
                                <div class="reasoning">
                                    <h5>Analysis Reasoning</h5>
                                    <p>${stockData.ai_analysis.reasoning}</p>
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}

                    <!-- Sentiment & Fundamentals -->
                    <div class="section fundamentals-section">
                        <h4><i class="fas fa-chart-bar"></i> Market Data</h4>
                        <div class="fundamentals-grid">
                            <!-- Sentiment Data -->
                            <div class="data-card">
                                <h5>Market Sentiment</h5>
                                <div class="sentiment-items">
                                    <div class="sentiment-item">
                                        <span class="label">News Sentiment:</span>
                                        <span class="value">${(stockData.sentiment_data.news_sentiment_score * 100).toFixed(0)}%</span>
                                    </div>
                                    <div class="sentiment-item">
                                        <span class="label">Social Sentiment:</span>
                                        <span class="value">${(stockData.sentiment_data.social_sentiment * 100).toFixed(0)}%</span>
                                    </div>
                                    <div class="sentiment-item">
                                        <span class="label">News Articles:</span>
                                        <span class="value">${stockData.sentiment_data.news_articles_count}</span>
                                    </div>
                                    <div class="sentiment-item">
                                        <span class="label">Analyst Rating:</span>
                                        <span class="analyst-rating ${stockData.sentiment_data.analyst_rating.toLowerCase()}">${stockData.sentiment_data.analyst_rating}</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Fundamental Data -->
                            <div class="data-card">
                                <h5>Fundamentals</h5>
                                <div class="fundamental-items">
                                    <div class="fundamental-item">
                                        <span class="label">P/E Ratio:</span>
                                        <span class="value">${stockData.fundamental_data.pe_ratio || 'N/A'}</span>
                                    </div>
                                    <div class="fundamental-item">
                                        <span class="label">Market Cap:</span>
                                        <span class="value">${stockData.fundamental_data.market_cap || 'N/A'}</span>
                                    </div>
                                    <div class="fundamental-item">
                                        <span class="label">Dividend Yield:</span>
                                        <span class="value">${stockData.fundamental_data.dividend_yield ? formatPercentage(stockData.fundamental_data.dividend_yield) : 'N/A'}</span>
                                    </div>
                                    <div class="fundamental-item">
                                        <span class="label">EPS (TTM):</span>
                                        <span class="value">${stockData.fundamental_data.eps_ttm || 'N/A'}</span>
                                    </div>
                                    <div class="fundamental-item">
                                        <span class="label">Revenue Growth:</span>
                                        <span class="value">${stockData.fundamental_data.revenue_growth ? formatPercentage(stockData.fundamental_data.revenue_growth) : 'N/A'}</span>
                                    </div>
                                    <div class="fundamental-item">
                                        <span class="label">Debt/Equity:</span>
                                        <span class="value">${stockData.fundamental_data.debt_to_equity || 'N/A'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
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
                        <div class="report-title">
                            <h4><i class="fas fa-file-alt"></i> Daily Report - ${formatDate(report.date)}</h4>
                            <span class="report-id">${report.report_id}</span>
                        </div>
                        <div class="report-meta">
                            <span class="report-type">${report.report_type || 'DAILY'}</span>
                            <span class="retrieved-time">Retrieved: ${formatDate(reportData.retrieved_at)}</span>
                        </div>
                    </div>

                    <!-- Market Overview Section -->
                    ${report.market_overview ? `
                        <div class="section market-overview-section">
                            <h5><i class="fas fa-globe"></i> Market Overview</h5>
                            <div class="market-overview-content">
                                <div class="sentiment-indicator sentiment-${(report.market_overview.market_sentiment || '').toLowerCase()}">
                                    <i class="fas fa-chart-line"></i>
                                    <span>Market Sentiment: <strong>${report.market_overview.market_sentiment || 'UNKNOWN'}</strong></span>
                                </div>
                                
                                ${report.market_overview.market_themes && report.market_overview.market_themes.length > 0 ? `
                                    <div class="market-themes">
                                        <h6>Key Market Themes:</h6>
                                        <div class="theme-tags">
                                            ${report.market_overview.market_themes.map(theme => `<span class="theme-tag">${theme}</span>`).join('')}
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Recommendations Section -->
                    <div class="section recommendations-section">
                        <h5><i class="fas fa-star"></i> Investment Recommendations</h5>
                        <div class="recommendations-grid">
                            <!-- Stable Recommendation -->
                            ${report.stable_recommendation ? `
                                <div class="recommendation-card stable-rec">
                                    <div class="rec-header">
                                        <div class="rec-icon"><i class="fas fa-shield-alt"></i></div>
                                        <div class="rec-info">
                                            <h6>Stable Investment</h6>
                                            <div class="rec-symbol">${report.stable_recommendation.symbol}</div>
                                        </div>
                                        <div class="rec-allocation">${formatCurrency(report.stable_recommendation.allocation)}</div>
                                    </div>
                                    <div class="rec-body">
                                        <div class="confidence-section">
                                            <span>Confidence: ${formatPercentage(report.stable_recommendation.confidence)}</span>
                                            <div class="confidence-bar">
                                                <div class="confidence-fill" style="width: ${(report.stable_recommendation.confidence || 0) * 100}%; background-color: ${getConfidenceColor(report.stable_recommendation.confidence)}"></div>
                                            </div>
                                        </div>
                                        <div class="risk-section">
                                            <span>Max Risk: ${formatPercentage(report.stable_recommendation.max_risk)}</span>
                                        </div>
                                        <div class="reasoning">
                                            <strong>Analysis:</strong>
                                            <p>${report.stable_recommendation.reasoning}</p>
                                        </div>
                                    </div>
                                </div>
                            ` : '<div class="no-recommendation">No stable recommendation available</div>'}

                            <!-- Risky Recommendation -->
                            ${report.risky_recommendation ? `
                                <div class="recommendation-card risky-rec">
                                    <div class="rec-header">
                                        <div class="rec-icon"><i class="fas fa-rocket"></i></div>
                                        <div class="rec-info">
                                            <h6>Risky Investment</h6>
                                            <div class="rec-symbol">${report.risky_recommendation.symbol}</div>
                                        </div>
                                        <div class="rec-allocation">${formatCurrency(report.risky_recommendation.allocation)}</div>
                                    </div>
                                    <div class="rec-body">
                                        <div class="confidence-section">
                                            <span>Confidence: ${formatPercentage(report.risky_recommendation.confidence)}</span>
                                            <div class="confidence-bar">
                                                <div class="confidence-fill" style="width: ${(report.risky_recommendation.confidence || 0) * 100}%; background-color: ${getConfidenceColor(report.risky_recommendation.confidence)}"></div>
                                            </div>
                                        </div>
                                        <div class="risk-section">
                                            <span>Max Risk: ${formatPercentage(report.risky_recommendation.max_risk)}</span>
                                        </div>
                                        <div class="reasoning">
                                            <strong>Analysis:</strong>
                                            <p>${report.risky_recommendation.reasoning}</p>
                                        </div>
                                    </div>
                                </div>
                            ` : '<div class="no-recommendation">No risky recommendation available</div>'}
                        </div>
                    </div>

                    <!-- Market Risks Section -->
                    ${report.market_risks && report.market_risks.length > 0 ? `
                        <div class="section risks-section">
                            <h5><i class="fas fa-exclamation-triangle"></i> Market Risks</h5>
                            <div class="risks-list">
                                ${report.market_risks.map(risk => `
                                    <div class="risk-item">
                                        <i class="fas fa-warning"></i>
                                        <span>${risk}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Report Statistics -->
                    <div class="section stats-section">
                        <h5><i class="fas fa-chart-bar"></i> Report Statistics</h5>
                        <div class="stats-grid">
                            <div class="stat-item">
                                <div class="stat-value">${report.analyzed_stocks_count || 0}</div>
                                <div class="stat-label">Stocks Analyzed</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${Math.round((report.processing_time_minutes || 0) * 100) / 100}m</div>
                                <div class="stat-label">Processing Time</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${formatPercentage(report.data_quality_score || 0)}</div>
                                <div class="stat-label">Data Quality</div>
                            </div>
                        </div>
                    </div>

                    <!-- Detailed Report Content -->
                    ${report.content ? `
                        <div class="section content-section">
                            <h5><i class="fas fa-document"></i> Detailed Analysis</h5>
                            <div class="report-text">
                                ${this.formatReportContent(report.content)}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (error) {
            showError('Failed to load latest report', 'latest-report');
        }
    }

    formatReportContent(content) {
        // Convert markdown-like content to HTML
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold text
            .replace(/### (.*)/g, '<h3>$1</h3>')              // Headers
            .replace(/- \*\*(.*?)\*\*/g, '<li><strong>$1</strong></li>')  // Bold list items
            .replace(/- (.*)/g, '<li>$1</li>')                // List items
            .replace(/\n\n/g, '</p><p>')                      // Paragraphs
            .replace(/\n/g, '<br>')                           // Line breaks
            .replace(/^/, '<p>')                              // Start paragraph
            .replace(/$/, '</p>');                            // End paragraph
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

    async loadLatestSummaryReport() {
        showLoading('summary-report');
        try {
            const result = await api.getLatestSummaryReport();
            
            // Use the same display logic as generateSummaryReport
            this.displaySummaryReport(result, true); // true = loaded, not generated
            
        } catch (error) {
            showError('Failed to load latest summary report. Make sure at least one summary report has been generated.', 'summary-report');
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
            this.displaySummaryReport(result, false); // false = generated, not loaded
            
        } catch (error) {
            showError('Failed to generate summary report', 'summary-report');
        }
    }

    displaySummaryReport(result, isLoaded = false) {
        const report = result.report;
            
            document.getElementById('summary-report').innerHTML = `
                <div class="summary-report-content">
                    <!-- Report Header -->
                    <div class="report-header">
                        <div class="report-title">
                            <h4><i class="fas fa-chart-area"></i> ${report.report_type || 'Summary Report'}</h4>
                            <span class="report-id">${report.report_id}</span>
                        </div>
                        <div class="report-meta">
                            <div class="period-info">
                                <i class="fas fa-calendar-alt"></i>
                                <span>${formatDate(report.start_date)} - ${formatDate(report.end_date)}</span>
                            </div>
                            <div class="generation-time">
                                <i class="fas fa-clock"></i>
                                <span>Generated: ${formatDate(result.generated_at)}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Period Overview -->
                    <div class="section period-overview-section">
                        <h5><i class="fas fa-info-circle"></i> Period Overview</h5>
                        <div class="overview-stats">
                            <div class="overview-stat">
                                <div class="stat-value">${report.days_analyzed}</div>
                                <div class="stat-label">Days Analyzed</div>
                            </div>
                            <div class="overview-stat">
                                <div class="stat-value">${report.performance_metrics?.total_recommendations || 0}</div>
                                <div class="stat-label">Total Recommendations</div>
                            </div>
                            <div class="overview-stat">
                                <div class="stat-value">${formatPercentage(report.performance_metrics?.avg_confidence_score || 0)}</div>
                                <div class="stat-label">Avg Confidence</div>
                            </div>
                            <div class="overview-stat">
                                <div class="stat-value">${report.performance_metrics?.stable_picks_count || 0}/${report.performance_metrics?.risky_picks_count || 0}</div>
                                <div class="stat-label">Stable/Risky</div>
                            </div>
                        </div>
                    </div>

                    <!-- Top Performers -->
                    <div class="section performers-section">
                        <h5><i class="fas fa-trophy"></i> Top Performers</h5>
                        <div class="performers-grid">
                            <!-- Stable Performers -->
                            <div class="performer-category">
                                <h6><i class="fas fa-shield-alt"></i> Top Stable Performers</h6>
                                <div class="performer-list">
                                    ${(report.top_stable_performers || []).map(performer => `
                                        <div class="performer-item">
                                            <div class="performer-symbol">${performer.symbol}</div>
                                            <div class="performer-stats">
                                                <span class="frequency">Recommended ${performer.frequency} time${performer.frequency !== 1 ? 's' : ''}</span>
                                                ${performer.avg_return ? `<span class="return">Avg Return: ${formatPercentage(performer.avg_return)}</span>` : ''}
                                            </div>
                                        </div>
                                    `).join('')}
                                    ${(report.top_stable_performers || []).length === 0 ? '<div class="no-data">No stable recommendations in this period</div>' : ''}
                                </div>
                            </div>

                            <!-- Risky Performers -->
                            <div class="performer-category">
                                <h6><i class="fas fa-rocket"></i> Top Risky Performers</h6>
                                <div class="performer-list">
                                    ${(report.top_risky_performers || []).map(performer => `
                                        <div class="performer-item">
                                            <div class="performer-symbol">${performer.symbol}</div>
                                            <div class="performer-stats">
                                                <span class="frequency">Recommended ${performer.frequency} time${performer.frequency !== 1 ? 's' : ''}</span>
                                                ${performer.avg_return ? `<span class="return">Avg Return: ${formatPercentage(performer.avg_return)}</span>` : ''}
                                            </div>
                                        </div>
                                    `).join('')}
                                    ${(report.top_risky_performers || []).length === 0 ? '<div class="no-data">No risky recommendations in this period</div>' : ''}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Market Trends -->
                    ${report.market_trends ? `
                        <div class="section market-trends-section">
                            <h5><i class="fas fa-chart-line"></i> Market Trends</h5>
                            <div class="trends-content">
                                <!-- Dominant Themes -->
                                ${report.market_trends.dominant_themes && report.market_trends.dominant_themes.length > 0 ? `
                                    <div class="themes-section">
                                        <h6>Dominant Themes</h6>
                                        <div class="theme-tags">
                                            ${report.market_trends.dominant_themes.map(theme => `<span class="theme-tag">${theme}</span>`).join('')}
                                        </div>
                                    </div>
                                ` : ''}

                                <!-- Sector Performance -->
                                ${report.market_trends.sector_performance ? `
                                    <div class="sector-performance">
                                        <h6>Sector Performance</h6>
                                        <div class="sector-grid">
                                            ${Object.entries(report.market_trends.sector_performance).map(([sector, performance]) => `
                                                <div class="sector-item">
                                                    <span class="sector-name">${sector.charAt(0).toUpperCase() + sector.slice(1)}</span>
                                                    <span class="sector-performance">${performance ? formatPercentage(performance) : 'N/A'}</span>
                                                </div>
                                            `).join('')}
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Key Insights -->
                    ${report.insights && report.insights.length > 0 ? `
                        <div class="section insights-section">
                            <h5><i class="fas fa-lightbulb"></i> Key Insights</h5>
                            <div class="insights-list">
                                ${report.insights.map(insight => `
                                    <div class="insight-item">
                                        <i class="fas fa-check-circle"></i>
                                        <span>${insight}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Next Month Outlook -->
                    ${report.next_month_outlook ? `
                        <div class="section outlook-section">
                            <h5><i class="fas fa-crystal-ball"></i> Next Month Outlook</h5>
                            <div class="outlook-content">
                                <p>${report.next_month_outlook.replace(/\n/g, '<br>')}</p>
                            </div>
                        </div>
                    ` : ''}

                    <!-- Detailed Report Content -->
                    ${report.content ? `
                        <div class="section detailed-content-section">
                            <h5><i class="fas fa-file-text"></i> Detailed Analysis</h5>
                            <div class="detailed-content">
                                ${this.formatReportContent(report.content)}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Success Message -->
                    <div class="success-message">
                        <i class="fas fa-check-circle"></i>
                        <span>Summary report ${isLoaded ? 'loaded' : 'generated'} successfully for ${report.days_analyzed} days of analysis</span>
                    </div>
                </div>
            `;
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