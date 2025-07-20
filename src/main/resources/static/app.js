// Fukui Shrine Navigator - Frontend JavaScript

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
        this.initializeToastContainer();
    }

    // Initialize toast notification container
    initializeToastContainer() {
        if (!document.getElementById('toast-container')) {
            const toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1050';
            document.body.appendChild(toastContainer);
        }
    }

    // Bind event handlers
    bindEvents() {
        // Search functionality
        document.getElementById('search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.performSearch();
        });

        // AI Q&A functionality
        document.getElementById('ask-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.askQuestion();
        });

        // Recommendation functionality
        document.getElementById('recommendation-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.getRecommendations();
        });

        // Geolocation functionality
        document.getElementById('get-location-btn').addEventListener('click', () => {
            this.getCurrentLocation();
        });

        document.getElementById('find-nearby-btn').addEventListener('click', () => {
            this.findNearbyPlaces();
        });

        // Statistics
        document.getElementById('load-stats-btn').addEventListener('click', () => {
            this.loadStats();
        });

        // Add suggestion pills for AI chat
        this.addSuggestionPills();
    }

    // Check API status
    async checkApiStatus() {
        const statusElement = document.getElementById('api-status');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                statusElement.textContent = 'API Online';
                statusElement.className = 'badge status-online';
                this.showToast('API Connected Successfully', 'success');
            } else {
                throw new Error('API Unhealthy');
            }
        } catch (error) {
            statusElement.textContent = 'API Offline';
            statusElement.className = 'badge status-offline';
            this.showToast('API Connection Failed', 'error');
            console.error('API status check failed:', error);
        }
    }

    // Load category options
    async loadCategories() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/categories`);
            const data = await response.json();
            
            if (data.success && data.data.categories) {
                const categorySelects = document.querySelectorAll('#search-category, #rec-category');
                
                categorySelects.forEach(select => {
                    // Clear existing options (keep first one)
                    while (select.children.length > 1) {
                        select.removeChild(select.lastChild);
                    }
                    
                    // Add new options
                    data.data.categories.forEach(category => {
                        const option = document.createElement('option');
                        option.value = category;
                        option.textContent = category;
                        select.appendChild(option);
                    });
                });
            }
        } catch (error) {
            console.error('Failed to load categories:', error);
            this.showToast('Failed to load categories', 'error');
        }
    }

    // Perform search
    async performSearch() {
        const query = document.getElementById('search-input').value.trim();
        const category = document.getElementById('search-category').value;
        const resultsContainer = document.getElementById('search-results');

        if (!query) {
            this.showError(resultsContainer, 'Please enter search keywords');
            this.showToast('Please enter search keywords', 'warning');
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
                this.showToast(`Found ${data.data.results.length} results`, 'success');
            } else {
                throw new Error('Search request failed');
            }
        } catch (error) {
            this.showError(resultsContainer, 'Search error occurred, please try again later');
            this.showToast('Search failed', 'error');
            console.error('Search error:', error);
        }
    }

    // Display search results
    displaySearchResults(container, results) {
        if (!results || results.length === 0) {
            container.innerHTML = '<div class="error-message">No relevant results found</div>';
            return;
        }

        const html = results.map(result => `
            <div class="result-item">
                <div class="result-title">${result.metadata?.name || 'Unknown Location'}</div>
                <div class="result-content">${result.content}</div>
                <div class="result-meta">
                    <span class="similarity-score">Similarity: ${(result.similarity_score * 100).toFixed(1)}%</span>
                    <span class="ms-2">Category: ${result.metadata?.category || 'Uncategorized'}</span>
                    ${result.metadata?.tags ? `<span class="ms-2">Tags: ${result.metadata.tags.join(', ')}</span>` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    // AI Q&A
    async askQuestion() {
        const query = document.getElementById('ask-input').value.trim();
        const resultsContainer = document.getElementById('ask-results');

        if (!query) {
            this.showError(resultsContainer, 'Please enter your question');
            this.showToast('Please enter your question', 'warning');
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
                this.showToast('AI response received', 'success');
            } else {
                throw new Error('Q&A request failed');
            }
        } catch (error) {
            this.showError(resultsContainer, 'AI Q&A service temporarily unavailable, please try again later');
            this.showToast('AI service unavailable', 'error');
            console.error('Q&A error:', error);
        }
    }

    // Display AI response
    displayAIResponse(container, data) {
        const html = `
            <div class="ai-response">
                <div class="answer">${data.answer}</div>
                <div class="confidence-score">
                    <i class="fas fa-brain me-1"></i>
                    Confidence: ${(data.confidence_score * 100).toFixed(1)}%
                </div>
            </div>
            ${data.sources && data.sources.length > 0 ? `
                <div class="mt-3">
                    <h6><i class="fas fa-info-circle me-1"></i>References:</h6>
                    ${data.sources.map(source => `
                        <div class="result-item">
                            <div class="result-title">${source.name || 'Unknown Source'}</div>
                            <div class="result-content">${source.content.substring(0, 200)}...</div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;

        container.innerHTML = html;
    }

    // Get recommendations
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
                this.showToast('Recommendations generated', 'success');
            } else {
                throw new Error('Recommendation request failed');
            }
        } catch (error) {
            this.showError(resultsContainer, 'Recommendation service temporarily unavailable, please try again later');
            this.showToast('Recommendation service unavailable', 'error');
            console.error('Recommendation error:', error);
        }
    }

    // Get current location
    getCurrentLocation() {
        const locationInfo = document.getElementById('location-info');
        const findNearbyBtn = document.getElementById('find-nearby-btn');

        if (!navigator.geolocation) {
            this.showError(locationInfo, 'Browser does not support geolocation');
            this.showToast('Geolocation not supported', 'error');
            return;
        }

        locationInfo.innerHTML = '<div class="loading-spinner"></div> Getting your location...';

        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };

                locationInfo.innerHTML = `
                    <div class="location-info">
                        <i class="fas fa-map-marker-alt me-2"></i>
                        Location acquired
                        <div class="location-coordinates">
                            Latitude: ${this.currentLocation.latitude.toFixed(6)}<br>
                            Longitude: ${this.currentLocation.longitude.toFixed(6)}
                        </div>
                    </div>
                `;

                findNearbyBtn.disabled = false;
                this.showToast('Location acquired successfully', 'success');
            },
            (error) => {
                let errorMessage = 'Unable to get location information';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = 'Location access denied, please check browser permissions';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = 'Location information unavailable';
                        break;
                    case error.TIMEOUT:
                        errorMessage = 'Location request timed out';
                        break;
                }
                this.showError(locationInfo, errorMessage);
                this.showToast('Location access failed', 'error');
            }
        );
    }

    // Find nearby places
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
                max_distance: 5000 // 5km
            });

            const response = await fetch(`${this.apiBaseUrl}/geofence/nearby?${params}`);
            const data = await response.json();

            if (data.success) {
                this.displayNearbyResults(resultsContainer, data.data.zones);
                this.showToast(`Found ${data.data.zones.length} nearby places`, 'success');
            } else {
                throw new Error('Nearby places query failed');
            }
        } catch (error) {
            this.showError(resultsContainer, 'Error occurred while searching nearby places');
            this.showToast('Nearby search failed', 'error');
            console.error('Nearby places error:', error);
        }
    }

    // Display nearby places results
    displayNearbyResults(container, zones) {
        if (!zones || zones.length === 0) {
            container.innerHTML = '<div class="error-message">No nearby places found</div>';
            return;
        }

        const html = zones.map(zone => `
            <div class="nearby-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${zone.name}</strong>
                        <div class="text-muted small">${zone.metadata?.category || 'Uncategorized'}</div>
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

    // Load statistics
    async loadStats() {
        const statsContent = document.getElementById('stats-content');
        this.showLoading(statsContent);

        try {
            const response = await fetch(`${this.apiBaseUrl}/stats`);
            const data = await response.json();

            if (data.success) {
                this.displayStats(statsContent, data.data);
                this.showToast('Statistics loaded', 'success');
            } else {
                throw new Error('Statistics loading failed');
            }
        } catch (error) {
            this.showError(statsContent, 'Unable to load statistics');
            this.showToast('Statistics unavailable', 'error');
            console.error('Statistics error:', error);
        }
    }

    // Display statistics
    displayStats(container, stats) {
        const dbStats = stats.database_stats || {};
        const config = stats.config || {};

        const html = `
            <div class="stats-grid">
                <div class="stats-item">
                    <div class="stats-number">${dbStats.total_chunks || 0}</div>
                    <div class="stats-label">Total Documents</div>
                </div>
                <div class="stats-item">
                    <div class="stats-number">${dbStats.categories?.length || 0}</div>
                    <div class="stats-label">Location Categories</div>
                </div>
                <div class="stats-item">
                    <div class="stats-number">${config.max_search_results || 0}</div>
                    <div class="stats-label">Max Search Results</div>
                </div>
                <div class="stats-item">
                    <div class="stats-number">${(config.similarity_threshold * 100).toFixed(0)}%</div>
                    <div class="stats-label">Similarity Threshold</div>
                </div>
            </div>
            <div class="mt-3">
                <h6>System Configuration:</h6>
                <ul>
                    <li>Model: ${config.model_name || 'Unknown'}</li>
                    <li>Database: ${dbStats.collection_name || 'Unknown'}</li>
                    <li>Path: ${dbStats.db_path || 'Unknown'}</li>
                </ul>
            </div>
        `;

        container.innerHTML = html;
    }

    // Add suggestion pills for AI chat
    addSuggestionPills() {
        const suggestions = [
            "What are the most famous shrines in Fukui?",
            "Tell me about temples with beautiful gardens",
            "Which places are good for meditation?",
            "Show me temples with historical significance"
        ];

        const askInput = document.getElementById('ask-input');
        if (askInput && askInput.parentNode) {
            const pillsContainer = document.createElement('div');
            pillsContainer.className = 'suggestion-pills mt-2';
            
            suggestions.forEach(suggestion => {
                const pill = document.createElement('button');
                pill.className = 'btn btn-outline-secondary btn-sm me-2 mb-2';
                pill.textContent = suggestion;
                pill.onclick = () => {
                    askInput.value = suggestion;
                    askInput.focus();
                };
                pillsContainer.appendChild(pill);
            });
            
            askInput.parentNode.insertBefore(pillsContainer, askInput.nextSibling);
        }
    }

    // Modern toast notification system
    showToast(message, type = 'info', duration = 4000) {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;

        const toastId = 'toast-' + Date.now();
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast show align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="${iconMap[type]} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;

        toastContainer.appendChild(toast);

        // Auto-remove after duration
        setTimeout(() => {
            const toastElement = document.getElementById(toastId);
            if (toastElement) {
                toastElement.classList.add('fade');
                setTimeout(() => toastElement.remove(), 300);
            }
        }, duration);
    }

    // Helper methods - Show loading state
    showLoading(container) {
        container.innerHTML = `
            <div class="text-center py-4">
                <div class="loading-spinner"></div>
                <div class="mt-2">Loading...</div>
            </div>
        `;
    }

    // Helper methods - Show error
    showError(container, message) {
        container.innerHTML = `<div class="error-message">${message}</div>`;
    }

    // Helper methods - Show success message
    showSuccess(container, message) {
        container.innerHTML = `<div class="success-message">${message}</div>`;
    }
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', () => {
    new ShrineNavigatorApp();
});

// Smooth scroll to anchors
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