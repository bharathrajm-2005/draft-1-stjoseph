document.addEventListener('DOMContentLoaded', () => {
    // Configuration
    const API_BASE_URL = '/api';
    const REFRESH_INTERVAL = 10000; // 10 seconds

    // State
    let feedbacks = [];
    let tasks = [];
    let lastRenderedHTML = '';
    let currentFilters = {
        dept: 'all',
        sentiment: 'all',
        status: 'active'
    };

    // DOM Elements
    const ticketGrid = document.getElementById('ticketGrid');
    const refreshBtn = document.getElementById('refreshBtn');
    const lastUpdateEl = document.getElementById('lastUpdate');

    const metricActive = document.getElementById('metricActive');
    const metricRating = document.getElementById('metricRating');
    const metricCritical = document.getElementById('metricCritical');
    const metricWait = document.getElementById('metricWait');

    const filterDept = document.getElementById('filterDept');
    const filterSentiment = document.getElementById('filterSentiment');
    const filterStatus = document.getElementById('filterStatus');

    // Initialization
    const init = async () => {
        setupEventListeners();
        await loadData();
        startPolling();
    };

    const setupEventListeners = () => {
        refreshBtn.addEventListener('click', loadData);

        filterDept.addEventListener('change', (e) => {
            currentFilters.dept = e.target.value;
            renderUI();
        });

        filterSentiment.addEventListener('change', (e) => {
            currentFilters.sentiment = e.target.value;
            renderUI();
        });

        filterStatus.addEventListener('change', (e) => {
            currentFilters.status = e.target.value;
            renderUI();
        });
    };

    const loadData = async () => {
        refreshBtn.classList.add('loading');
        try {
            const [fRes, tRes] = await Promise.all([
                fetch(`${API_BASE_URL}/get-feedback`),
                fetch(`${API_BASE_URL}/tasks`)
            ]);

            const fData = await fRes.json();
            const tData = await tRes.json();

            feedbacks = fData.data || [];
            tasks = tData.data || [];

            updateDepartmentDropdown(tasks);
            renderUI();
            updateLastRefreshTime();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            showToast('Failed to sync with server');
        } finally {
            refreshBtn.classList.remove('loading');
        }
    };

    const startPolling = () => {
        setInterval(loadData, REFRESH_INTERVAL);
    };

    const updateLastRefreshTime = () => {
        const now = new Date();
        lastUpdateEl.textContent = `Last sync: ${now.toLocaleTimeString()}`;
    };

    const renderUI = () => {
        const mergedData = mergeAndFilterData();
        const sortedData = sortData(mergedData);

        renderMetrics(feedbacks, tasks);
        renderTickets(sortedData);
    };

    const mergeAndFilterData = () => {
        // Map tasks to feedbacks
        const taskMap = {};
        tasks.forEach(t => {
            taskMap[t.feedback_id] = t;
        });

        let merged = feedbacks.map(f => {
            const task = taskMap[f.id];
            return {
                ...f,
                taskId: task ? task.id : null,
                department: task ? task.department : 'N/A',
                status: task ? task.status : 'N/A'
            };
        });

        // Apply filters
        return merged.filter(item => {
            const deptMatch = currentFilters.dept === 'all' || String(item.department).trim() === currentFilters.dept;
            const sentimentMatch = currentFilters.sentiment === 'all' || String(item.sentiment).trim() === currentFilters.sentiment;

            let statusMatch = true;
            if (currentFilters.status === 'active') {
                statusMatch = item.status === 'Open' || item.status === 'In Progress';
            } else if (currentFilters.status !== 'all') {
                statusMatch = item.status === currentFilters.status;
            }

            const isTicket = item.taskId !== null;
            return deptMatch && sentimentMatch && statusMatch && isTicket;
        });
    };

    const updateDepartmentDropdown = (taskList) => {
        const depts = [...new Set(taskList.map(t => t.department))].sort();
        const currentValue = filterDept.value;

        // Keep "All Departments" and add others
        let html = '<option value="all">All Departments</option>';
        depts.forEach(d => {
            if (d && d !== 'N/A') {
                html += `<option value="${d}" ${d === currentValue ? 'selected' : ''}>${d}</option>`;
            }
        });

        // Only update if list has changed to avoid flickering while clicking
        if (filterDept.innerHTML !== html) {
            filterDept.innerHTML = html;
        }
    };

    const sortData = (data) => {
        const sentimentPriority = { 'Negative': 0, 'Neutral': 1, 'Positive': 2 };
        const statusPriority = { 'Open': 0, 'In Progress': 1, 'Resolved': 2 };

        return [...data].sort((a, b) => {
            // 1. Status Priority
            const sA = statusPriority[a.status] ?? 3;
            const sB = statusPriority[b.status] ?? 3;
            if (sA !== sB) return sA - sB;

            // 2. Sentiment Priority
            const sentA = sentimentPriority[a.sentiment] ?? 3;
            const sentB = sentimentPriority[b.sentiment] ?? 3;
            if (sentA !== sentB) return sentA - sentB;

            // 3. Date (Newest first)
            return new Date(b.created_at) - new Date(a.created_at);
        });
    };

    const renderMetrics = (fList, tList) => {
        const activeCount = tList.filter(t => t.status !== 'Resolved').length;
        metricActive.textContent = activeCount;

        const totalRating = fList.reduce((acc, f) => acc + (f.rating || 0), 0);
        const avg = fList.length > 0 ? (totalRating / fList.length).toFixed(1) : '0.0';
        metricRating.textContent = `${avg}/5.0`;

        const criticalCount = fList.filter(f => f.severity === 'High').length;
        metricCritical.textContent = criticalCount;

        const waitCount = tList.filter(t => t.department === 'Wait Time').length;
        metricWait.textContent = waitCount;
    };

    const renderTickets = (data) => {
        if (data.length === 0) {
            ticketGrid.innerHTML = `
                <div class="loading-state">
                    <p>No active tickets found matching your filters.</p>
                </div>
            `;
            return;
        }

        const newHTML = data.map(ticket => {
            const sentimentClass = ticket.sentiment.toLowerCase();
            const statusClass = ticket.status.toLowerCase().replace(' ', '-');

            return `
                <div class="ticket-card ${sentimentClass.substring(0, 3)}" data-id="${ticket.taskId}">
                    <div class="ticket-info">
                        <div class="ticket-head">
                            <h3>Ticket #${ticket.taskId} — Patient ${ticket.patient_id}</h3>
                            <span class="badge badge-status-${statusClass}">${ticket.status}</span>
                        </div>
                        <div class="ticket-meta">
                            <strong>Dept:</strong> ${ticket.department} &nbsp;|&nbsp; 
                            <strong>Sentiment:</strong> <span class="sentiment-${sentimentClass}">${ticket.sentiment}</span>
                        </div>
                        <p class="ticket-text">"${ticket.feedback_text}"</p>
                        <div class="ticket-meta">
                            <small>Received: ${new Date(ticket.created_at).toLocaleString()}</small>
                        </div>
                    </div>
                    <div class="ticket-actions">
                        <label style="font-size: 0.75rem; color: var(--text-muted)">Update Status</label>
                        <select class="status-select" onchange="window.handleStatusUpdate(${ticket.taskId}, this.value)">
                            <option value="Open" ${ticket.status === 'Open' ? 'selected' : ''}>Open</option>
                            <option value="In Progress" ${ticket.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                            <option value="Resolved" ${ticket.status === 'Resolved' ? 'selected' : ''}>Resolved</option>
                        </select>
                    </div>
                </div>
            `;
        }).join('');

        // Flicker-free update: only replace if content changed
        if (lastRenderedHTML !== newHTML) {
            ticketGrid.innerHTML = newHTML;
            lastRenderedHTML = newHTML;
        }
    };

    // Global exposed function for status updates
    window.handleStatusUpdate = async (taskId, newStatus) => {
        try {
            const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });

            if (response.ok) {
                showToast(`Ticket #${taskId} updated to ${newStatus}`);
                await loadData();
            } else {
                showToast('Failed to update ticket status', true);
            }
        } catch (error) {
            console.error('Error updating status:', error);
            showToast('Network error while updating status', true);
        }
    };

    const showToast = (message, isError = false) => {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = 'toast';
        if (isError) toast.style.backgroundColor = 'var(--sentiment-neg)';
        toast.textContent = message;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    init();
});
