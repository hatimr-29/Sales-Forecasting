// ==========================================
// Global Variables for Chart Instances
// ==========================================
let salesChartInstance = null;
let pieChartInstance = null;
let regionChartInstance = null;
let productChartInstance = null;

// ==========================================
// Currency and Number Format Helpers
// ==========================================
function formatCurrency(num) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(num);
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-IN').format(num);
}

// ==========================================
// Initialize Dashboard Data and Charts
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // Check if we are on the dashboard sections
    if (document.getElementById('dashboard-section')) {
        loadStats();
        loadCharts();
    }
});

// ==========================================
// Fetch and Render KPI Stats
// ==========================================
function loadStats() {
    fetch('/api/stats')
        .then(response => {
            if (!response.ok) throw new Error('Unauthorized or network error');
            return response.json();
        })
        .then(data => {
            // Update stats cards
            document.getElementById('stat-total-sales').innerText = formatCurrency(data.total_sales);
            document.getElementById('stat-total-orders').innerText = formatNumber(data.total_orders);
            document.getElementById('stat-total-customers').innerText = formatNumber(data.total_customers);
            
            const growthEl = document.getElementById('stat-growth-rate');
            const growthValue = data.growth_rate;
            growthEl.innerText = (growthValue >= 0 ? '+' : '') + growthValue.toFixed(2) + '%';
            
            // Set color based on positive/negative growth
            if (growthValue >= 0) {
                growthEl.style.color = '#16a34a'; // Green
            } else {
                growthEl.style.color = '#dc2626'; // Red
            }

            // Populate Recent Transactions Table
            const tbody = document.getElementById('recent-orders-table-body');
            tbody.innerHTML = '';
            
            if (data.recent_orders && data.recent_orders.length > 0) {
                data.recent_orders.forEach(order => {
                    let badgeClass = 'bg-secondary';
                    if (order.status === 'Completed') badgeClass = 'bg-success';
                    else if (order.status === 'Pending') badgeClass = 'bg-warning text-dark';
                    else if (order.status === 'Shipped') badgeClass = 'bg-info';
                    else if (order.status === 'Cancelled') badgeClass = 'bg-danger';

                    const rowHtml = `
                        <tr>
                            <td class="ps-4 fw-semibold text-secondary">#${order.order_id}</td>
                            <td>
                                <div class="d-flex align-items-center">
                                    <div class="avatar-sm me-2 bg-light text-primary rounded-circle d-flex justify-content-center align-items-center" style="width:32px; height:32px; font-weight:600; font-size:13px;">
                                        ${order.customer.split(' ').map(n=>n[0]).join('')}
                                    </div>
                                    <span class="fw-medium">${order.customer}</span>
                                </div>
                            </td>
                            <td>${order.product}</td>
                            <td class="fw-semibold">${formatCurrency(order.amount)}</td>
                            <td class="pe-4"><span class="badge ${badgeClass}">${order.status}</span></td>
                        </tr>
                    `;
                    tbody.insertAdjacentHTML('beforeend', rowHtml);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3 text-muted">No recent transactions.</td></tr>';
            }
        })
        .catch(err => {
            console.error('Error loading statistics:', err);
        });
}

// ==========================================
// Fetch and Render Charts
// ==========================================
function loadCharts() {
    const year = document.getElementById('yearFilter').value;
    
    fetch(`/api/charts?year=${year}`)
        .then(response => response.json())
        .then(data => {
            renderSalesChart(data.monthly, year);
            renderPieChart(data.categories.labels, data.categories.values);
            renderRegionChart(data.regions.labels, data.regions.values);
            renderProductChart(data.products.labels, data.products.values);
        })
        .catch(err => {
            console.error('Error loading charts data:', err);
        });
}

// 1. Sales Trend Line Chart
function renderSalesChart(monthlyData, year) {
    const ctx = document.getElementById('salesChart').getContext('2d');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    if (salesChartInstance) {
        salesChartInstance.destroy();
    }
    
    salesChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: `Monthly Revenue in ${year}`,
                data: monthlyData,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.08)',
                fill: true,
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: '#4f46e5',
                tension: 0.35
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
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + (value / 100000).toFixed(0) + 'L';
                        }
                    }
                }
            }
        }
    });
}

// 2. Sales by Category Doughnut Chart
function renderPieChart(labels, values) {
    const ctx = document.getElementById('pieChart').getContext('2d');
    
    if (pieChartInstance) {
        pieChartInstance.destroy();
    }
    
    pieChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#ec4899'],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 15 }
                }
            }
        }
    });
}

// 3. Sales by Region Bar Chart
function renderRegionChart(labels, values) {
    const ctx = document.getElementById('regionChart').getContext('2d');
    
    if (regionChartInstance) {
        regionChartInstance.destroy();
    }
    
    regionChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: '#3b82f6',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + (value / 10000000).toFixed(1) + 'Cr';
                        }
                    }
                }
            }
        }
    });
}

// 4. Top 5 Selling Products Bar Chart
function renderProductChart(labels, values) {
    const ctx = document.getElementById('productChart').getContext('2d');
    
    if (productChartInstance) {
        productChartInstance.destroy();
    }
    
    productChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: '#10b981',
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₹' + (value / 10000000).toFixed(1) + 'Cr';
                        }
                    }
                }
            }
        }
    });
}

// ==========================================
// Machine Learning Forecasting Handler
// ==========================================
function runForecast(event) {
    event.preventDefault();
    
    const quantity = document.getElementById('forecast-quantity').value;
    const unitPrice = document.getElementById('forecast-unit-price').value;
    const date = document.getElementById('forecast-date').value;
    
    if (!quantity || !unitPrice || !date) {
        alert('Please fill out all forecasting parameters.');
        return;
    }
    
    const placeholder = document.getElementById('predictionPlaceholder');
    const loading = document.getElementById('predictionLoading');
    const result = document.getElementById('predictionResult');
    
    // Switch states: show loading spinner
    placeholder.setAttribute('style', 'display: none !important;');
    result.setAttribute('style', 'display: none !important;');
    loading.setAttribute('style', 'display: flex !important;');
    
    // Send API Request
    fetch('/api/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            quantity: parseInt(quantity),
            unit_price: parseFloat(unitPrice),
            date: date
        })
    })
    .then(response => {
        if (!response.ok) throw new Error('Prediction API failed');
        return response.json();
    })
    .then(data => {
        // Stop loading state
        loading.setAttribute('style', 'display: none !important;');
        result.setAttribute('style', 'display: flex !important;');
        
        // Render Output
        document.getElementById('res-prediction').innerText = formatCurrency(data.prediction);
        document.getElementById('res-baseline').innerText = formatCurrency(data.baseline);
        
        const adjEl = document.getElementById('res-adjustment');
        const adjValue = data.difference;
        adjEl.innerText = (adjValue >= 0 ? '+' : '') + formatCurrency(adjValue);
        adjEl.style.color = adjValue >= 0 ? '#10b981' : '#ef4444'; // Green or Red
        
        const pctEl = document.getElementById('res-adjustment-pct');
        pctEl.innerText = (data.diff_percent >= 0 ? '+' : '') + data.diff_percent.toFixed(1) + '%';
        pctEl.style.color = data.diff_percent >= 0 ? '#10b981' : '#ef4444';
        
        // Extracted Features Badges
        const featuresContainer = document.getElementById('res-features');
        featuresContainer.innerHTML = '';
        
        const features = data.features;
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const monthName = monthNames[features.Month - 1];
        
        const badges = [
            { icon: 'fa-calendar-days', label: `Year: ${features.Year}` },
            { icon: 'fa-calendar-minus', label: `Month: ${monthName}` },
            { icon: 'fa-chart-pie', label: `Quarter: Q${features.Quarter}` },
            { icon: 'fa-calendar-day', label: features.IsWeekend ? 'Weekend: Yes' : 'Weekend: No' }
        ];
        
        badges.forEach(b => {
            const badgeHtml = `
                <span class="feature-badge">
                    <i class="fa-solid ${b.icon} text-primary me-1"></i> ${b.label}
                </span>
            `;
            featuresContainer.insertAdjacentHTML('beforeend', badgeHtml);
        });
    })
    .catch(err => {
        console.error('Forecasting error:', err);
        loading.setAttribute('style', 'display: none !important;');
        placeholder.setAttribute('style', 'display: flex !important;');
        alert('Failed to calculate forecast. Check console or make sure Flask is running.');
    });
}