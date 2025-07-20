// 福井神社導航 - 前端 JavaScript

class ShrineNavigatorApp {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000';
        this.currentLocation = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkApiStatus();
        this.loadCategories();
    }

    // 綁定事件處理器
    bindEvents() {
        // 搜尋功能
        document.getElementById('search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.performSearch();
        });

        // AI 問答功能
        document.getElementById('ask-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.askQuestion();
        });

        // 推薦功能
        document.getElementById('recommendation-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.getRecommendations();
        });

        // 地理位置功能
        document.getElementById('get-location-btn').addEventListener('click', () => {
            this.getCurrentLocation();
        });

        document.getElementById('find-nearby-btn').addEventListener('click', () => {
            this.findNearbyPlaces();
        });

        // 統計資訊
        document.getElementById('load-stats-btn').addEventListener('click', () => {
            this.loadStats();
        });
    }

    // 檢查 API 狀態
    async checkApiStatus() {
        const statusElement = document.getElementById('api-status');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                statusElement.textContent = 'API 運行正常';
                statusElement.className = 'badge status-online';
            } else {
                throw new Error('API 不健康');
            }
        } catch (error) {
            statusElement.textContent = 'API 連接失敗';
            statusElement.className = 'badge status-offline';
            console.error('API 狀態檢查失敗:', error);
        }
    }

    // 載入類別選項
    async loadCategories() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/categories`);
            const data = await response.json();
            
            if (data.success && data.data.categories) {
                const categorySelects = document.querySelectorAll('#search-category, #rec-category');
                
                categorySelects.forEach(select => {
                    // 清除現有選項（保留第一個）
                    while (select.children.length > 1) {
                        select.removeChild(select.lastChild);
                    }
                    
                    // 添加新選項
                    data.data.categories.forEach(category => {
                        const option = document.createElement('option');
                        option.value = category;
                        option.textContent = category;
                        select.appendChild(option);
                    });
                });
            }
        } catch (error) {
            console.error('載入類別失敗:', error);
        }
    }

    // 執行搜尋
    async performSearch() {
        const query = document.getElementById('search-input').value.trim();
        const category = document.getElementById('search-category').value;
        const resultsContainer = document.getElementById('search-results');

        if (!query) {
            this.showError(resultsContainer, '請輸入搜尋關鍵詞');
            return;
        }

        this.showLoading(resultsContainer);

        try {
            const requestBody = {
                query: query,
                max_results: 10,
                category: category || null
            };

            const response = await fetch(`${this.apiBaseUrl}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (data.success) {
                this.displaySearchResults(resultsContainer, data.data.results);
            } else {
                throw new Error('搜尋請求失敗');
            }
        } catch (error) {
            this.showError(resultsContainer, '搜尋時發生錯誤，請稍後再試');
            console.error('搜尋錯誤:', error);
        }
    }

    // 顯示搜尋結果
    displaySearchResults(container, results) {
        if (!results || results.length === 0) {
            container.innerHTML = '<div class="error-message">沒有找到相關結果</div>';
            return;
        }

        const html = results.map(result => `
            <div class="result-item">
                <div class="result-title">${result.metadata?.name || '未知地點'}</div>
                <div class="result-content">${result.content}</div>
                <div class="result-meta">
                    <span class="similarity-score">相似度: ${(result.similarity_score * 100).toFixed(1)}%</span>
                    <span class="ms-2">類別: ${result.metadata?.category || '未分類'}</span>
                    ${result.metadata?.tags ? `<span class="ms-2">標籤: ${result.metadata.tags.join(', ')}</span>` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    // AI 問答
    async askQuestion() {
        const query = document.getElementById('ask-input').value.trim();
        const resultsContainer = document.getElementById('ask-results');

        if (!query) {
            this.showError(resultsContainer, '請輸入您的問題');
            return;
        }

        this.showLoading(resultsContainer);

        try {
            const response = await fetch(`${this.apiBaseUrl}/ask`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            });

            const data = await response.json();

            if (data.success) {
                this.displayAIResponse(resultsContainer, data.data);
            } else {
                throw new Error('問答請求失敗');
            }
        } catch (error) {
            this.showError(resultsContainer, 'AI 問答服務暫時不可用，請稍後再試');
            console.error('問答錯誤:', error);
        }
    }

    // 顯示 AI 回應
    displayAIResponse(container, data) {
        const html = `
            <div class="ai-response">
                <div class="answer">${data.answer}</div>
                <div class="confidence-score">
                    <i class="fas fa-brain me-1"></i>
                    信心度: ${(data.confidence_score * 100).toFixed(1)}%
                </div>
            </div>
            ${data.sources && data.sources.length > 0 ? `
                <div class="mt-3">
                    <h6><i class="fas fa-info-circle me-1"></i>參考來源:</h6>
                    ${data.sources.map(source => `
                        <div class="result-item">
                            <div class="result-title">${source.name || '未知來源'}</div>
                            <div class="result-content">${source.content.substring(0, 200)}...</div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;

        container.innerHTML = html;
    }

    // 獲取推薦
    async getRecommendations() {
        const category = document.getElementById('rec-category').value;
        const interests = document.getElementById('rec-interests').value.trim();
        const resultsContainer = document.getElementById('recommendation-results');

        this.showLoading(resultsContainer);

        try {
            const requestBody = {
                category: category || null,
                interests: interests ? interests.split(',').map(i => i.trim()) : null,
                location_type: null
            };

            const response = await fetch(`${this.apiBaseUrl}/recommendations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (data.success) {
                this.displayAIResponse(resultsContainer, data.data);
            } else {
                throw new Error('推薦請求失敗');
            }
        } catch (error) {
            this.showError(resultsContainer, '推薦服務暫時不可用，請稍後再試');
            console.error('推薦錯誤:', error);
        }
    }

    // 獲取當前位置
    getCurrentLocation() {
        const locationInfo = document.getElementById('location-info');
        const findNearbyBtn = document.getElementById('find-nearby-btn');

        if (!navigator.geolocation) {
            this.showError(locationInfo, '瀏覽器不支援地理位置功能');
            return;
        }

        locationInfo.innerHTML = '<div class="loading-spinner"></div> 正在獲取位置...';

        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };

                locationInfo.innerHTML = `
                    <div class="location-info">
                        <i class="fas fa-map-marker-alt me-2"></i>
                        已獲取您的位置
                        <div class="location-coordinates">
                            緯度: ${this.currentLocation.latitude.toFixed(6)}<br>
                            經度: ${this.currentLocation.longitude.toFixed(6)}
                        </div>
                    </div>
                `;

                findNearbyBtn.disabled = false;
            },
            (error) => {
                let errorMessage = '無法獲取位置信息';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = '位置存取被拒絕，請檢查瀏覽器權限設定';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = '位置信息無法獲取';
                        break;
                    case error.TIMEOUT:
                        errorMessage = '獲取位置超時';
                        break;
                }
                this.showError(locationInfo, errorMessage);
            }
        );
    }

    // 尋找附近地點
    async findNearbyPlaces() {
        if (!this.currentLocation) {
            this.getCurrentLocation();
            return;
        }

        const resultsContainer = document.getElementById('nearby-results');
        this.showLoading(resultsContainer);

        try {
            const params = new URLSearchParams({
                latitude: this.currentLocation.latitude,
                longitude: this.currentLocation.longitude,
                max_distance: 5000 // 5公里
            });

            const response = await fetch(`${this.apiBaseUrl}/geofence/nearby?${params}`);
            const data = await response.json();

            if (data.success) {
                this.displayNearbyResults(resultsContainer, data.data.zones);
            } else {
                throw new Error('附近地點查詢失敗');
            }
        } catch (error) {
            this.showError(resultsContainer, '查詢附近地點時發生錯誤');
            console.error('附近地點錯誤:', error);
        }
    }

    // 顯示附近地點結果
    displayNearbyResults(container, zones) {
        if (!zones || zones.length === 0) {
            container.innerHTML = '<div class="error-message">附近沒有找到相關地點</div>';
            return;
        }

        const html = zones.map(zone => `
            <div class="nearby-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${zone.name}</strong>
                        <div class="text-muted small">${zone.metadata?.category || '未分類'}</div>
                    </div>
                    <span class="distance-badge">
                        ${zone.distance < 1000 ? 
                            `${Math.round(zone.distance)}m` : 
                            `${(zone.distance / 1000).toFixed(1)}km`
                        }
                    </span>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    // 載入統計資訊
    async loadStats() {
        const statsContent = document.getElementById('stats-content');
        this.showLoading(statsContent);

        try {
            const response = await fetch(`${this.apiBaseUrl}/stats`);
            const data = await response.json();

            if (data.success) {
                this.displayStats(statsContent, data.data);
            } else {
                throw new Error('統計資訊載入失敗');
            }
        } catch (error) {
            this.showError(statsContent, '無法載入統計資訊');
            console.error('統計資訊錯誤:', error);
        }
    }

    // 顯示統計資訊
    displayStats(container, stats) {
        const dbStats = stats.database_stats || {};
        const config = stats.config || {};

        const html = `
            <div class="stats-grid">
                <div class="stats-item">
                    <div class="stats-number">${dbStats.total_chunks || 0}</div>
                    <div class="stats-label">總文檔數</div>
                </div>
                <div class="stats-item">
                    <div class="stats-number">${dbStats.categories?.length || 0}</div>
                    <div class="stats-label">地點類別</div>
                </div>
                <div class="stats-item">
                    <div class="stats-number">${config.max_search_results || 0}</div>
                    <div class="stats-label">最大搜尋結果</div>
                </div>
                <div class="stats-item">
                    <div class="stats-number">${(config.similarity_threshold * 100).toFixed(0)}%</div>
                    <div class="stats-label">相似度門檻</div>
                </div>
            </div>
            <div class="mt-3">
                <h6>系統配置:</h6>
                <ul>
                    <li>模型: ${config.model_name || 'Unknown'}</li>
                    <li>資料庫: ${dbStats.collection_name || 'Unknown'}</li>
                    <li>路徑: ${dbStats.db_path || 'Unknown'}</li>
                </ul>
            </div>
        `;

        container.innerHTML = html;
    }

    // 輔助方法 - 顯示載入狀態
    showLoading(container) {
        container.innerHTML = `
            <div class="text-center py-4">
                <div class="loading-spinner"></div>
                <div class="mt-2">載入中...</div>
            </div>
        `;
    }

    // 輔助方法 - 顯示錯誤
    showError(container, message) {
        container.innerHTML = `<div class="error-message">${message}</div>`;
    }

    // 輔助方法 - 顯示成功訊息
    showSuccess(container, message) {
        container.innerHTML = `<div class="success-message">${message}</div>`;
    }
}

// 當頁面載入完成時初始化應用
document.addEventListener('DOMContentLoaded', () => {
    new ShrineNavigatorApp();
});

// 平滑滾動到錨點
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});