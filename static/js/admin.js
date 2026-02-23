/**
 * AUREVIA HOSPITAL INCIDENT INTELLIGENCE
 * FULLY AUTOMATED SMART ASSIGNMENT SYSTEM
 */

document.addEventListener('DOMContentLoaded', () => {
    // Configuration & State
    const API_BASE_URL = '/api';
    const REFRESH_INTERVAL = 10000; // 10 seconds — catches staff resolutions quickly
    let activeTickets = [];
    let currentTicketId = null;
    let refreshTimer = null;
    let slaTimerInterval = null;

    const filters = {
        department: 'all',
        sentiment: 'all',
        status: 'active'
    };

    // DOM Elements
    const elements = {
        ticketGrid: document.getElementById('ticketGrid'),
        metrics: {
            active: document.getElementById('metricActive'),
            rating: document.getElementById('metricRating'),
            critical: document.getElementById('metricCritical'),
            wait: document.getElementById('metricWait'),
        },
        sidebar: {
            deptFilter: document.getElementById('filterDept'),
            sentimentFilter: document.getElementById('filterSentiment'),
            statusFilter: document.getElementById('filterStatus'),
            viewAnalytics: document.getElementById('showAnalyticsBtn'),
            viewHeatmap: document.getElementById('showHeatmapBtn'),
            viewAppointments: document.getElementById('showAppointmentsBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            lastUpdate: document.getElementById('lastUpdate')
        },
        views: {
            ticketView: document.querySelector('.ticket-view'),
            analyticsView: document.getElementById('analyticsSection'),
            heatmapView: document.getElementById('heatmapSection'),
            appointmentsView: document.getElementById('appointmentsSection')
        },
        detailPanel: {
            panel: document.getElementById('detailPanel'),
            overlay: document.getElementById('detailOverlay'),
            close: document.getElementById('closePanel'),
            id: document.getElementById('detailTicketId'),
            dept: document.getElementById('detailDepartmentName'),
            status: document.getElementById('detailStatusBadge'),
            severity: document.getElementById('detailSeverityBadge'),
            countdown: document.getElementById('detailSLACountdown'),
            patientId: document.getElementById('detailPatientId'),
            sentiment: document.getElementById('detailSentiment'),
            received: document.getElementById('detailReceived'),
            feedbackText: document.getElementById('detailFeedbackText'),
            aiResponseDraft: document.getElementById('aiResponseDraft'),
            regenerateBtn: document.getElementById('regenerateBtn'),
            approveResponseBtn: document.getElementById('approveResponseBtn'),
            aiAssigningStatus: document.getElementById('aiAssigningStatus'),
            autoAssignedDoctorInfo: document.getElementById('autoAssignedDoctorInfo'),
            resolveBtn: document.getElementById('resolveBtn'),
            history: document.getElementById('statusHistory')
        }
    };

    // --- INITIALIZATION ---
    function init() {
        loadDashboardState();
        setupEventListeners();
        setupPolling();
        startSLAUpdates();
        populateDepartmentFilter();
    }

    function setupEventListeners() {
        elements.sidebar.deptFilter.addEventListener('change', (e) => {
            filters.department = e.target.value;
            loadTickets();
        });
        elements.sidebar.sentimentFilter.addEventListener('change', (e) => {
            filters.sentiment = e.target.value;
            loadTickets();
        });
        elements.sidebar.statusFilter.addEventListener('change', (e) => {
            filters.status = e.target.value;
            loadTickets();
        });

        elements.sidebar.viewAnalytics.addEventListener('click', () => switchView('analytics'));
        elements.sidebar.viewHeatmap.addEventListener('click', () => switchView('heatmap'));
        if (elements.sidebar.viewAppointments)
            elements.sidebar.viewAppointments.addEventListener('click', () => switchView('appointments'));
        elements.sidebar.refreshBtn.addEventListener('click', loadDashboardState);

        const closeAnalytics = document.getElementById('closeAnalytics');
        const closeHeatmap = document.getElementById('closeHeatmap');
        const closeAppointments = document.getElementById('closeAppointments');
        if (closeAnalytics) closeAnalytics.addEventListener('click', () => switchView('tickets'));
        if (closeHeatmap) closeHeatmap.addEventListener('click', () => switchView('tickets'));
        if (closeAppointments) closeAppointments.addEventListener('click', () => switchView('tickets'));

        elements.detailPanel.close.addEventListener('click', closeDetailPanel);
        elements.detailPanel.overlay.addEventListener('click', closeDetailPanel);
        elements.detailPanel.resolveBtn.addEventListener('click', handleResolution);
        elements.detailPanel.regenerateBtn.addEventListener('click', handleRegenerateResponse);
        elements.detailPanel.approveResponseBtn.addEventListener('click', handleApproveResponse);
    }

    // --- DATA LOADING ---
    async function loadDashboardState() {
        await Promise.all([loadMetrics(), loadTickets()]);
        updateLastSyncTime();
    }

    async function loadMetrics() {
        try {
            const res = await fetch(`${API_BASE_URL}/stats/dashboard`);
            const json = await res.json();
            if (json.status === 'success') {
                const { data } = json;
                elements.metrics.active.textContent = data.activeTickets || 0;
                elements.metrics.rating.textContent = data.averageRating || 0;
                elements.metrics.critical.textContent = data.criticalCases || 0;
                elements.metrics.wait.textContent = data.waitTimeAlert || 0;
            } else {
                console.error('Metrics Error:', json.message);
            }
        } catch (e) { console.error('Metrics Fetch Error:', e); }
    }

    async function loadTickets() {
        try {
            showLoading(true);
            const params = new URLSearchParams(filters);
            const res = await fetch(`${API_BASE_URL}/tickets?${params}`);
            const json = await res.json();

            if (json.status === 'success') {
                activeTickets = json.data || [];
                renderTicketGrid();
            } else {
                console.error('Tickets Error:', json.message);
                elements.ticketGrid.innerHTML = `<div class="error-state">Error: ${json.message}</div>`;
            }
            showLoading(false);
        } catch (e) {
            console.error('Tickets Fetch Error:', e);
            elements.ticketGrid.innerHTML = `<div class="error-state">Connection failed. Check server status.</div>`;
            showLoading(false);
        }
    }

    async function populateDepartmentFilter() {
        const departments = [
            "Emergency", "Cardiology", "Neurology", "Orthopedics", "Billing",
            "Pharmacy", "General Medicine", "Radiology", "ICU", "Administration"
        ];
        departments.forEach(dept => {
            const opt = document.createElement('option');
            opt.value = dept;
            opt.textContent = dept;
            elements.sidebar.deptFilter.appendChild(opt);
        });
    }

    // --- RENDERING ---
    function renderTicketGrid() {
        if (activeTickets.length === 0) {
            elements.ticketGrid.innerHTML = '<div class="loading-state">No tickets found matching filters.</div>';
            return;
        }

        elements.ticketGrid.innerHTML = activeTickets.map(ticket => {
            const isBreached = new Date(ticket.sla_deadline) < new Date();
            const isResolved = ticket.status === 'Resolved';
            let stateClass = isResolved ? 'state-resolved' : (isBreached ? 'state-breached' : 'state-pending');
            const slaDisplay = isResolved ? 'COMPLETED' : getSLAStatus(ticket.sla_deadline);
            const verifiedBadge = ticket.is_verified
                ? `<div class="verified-pill">🟢 Verified Patient</div>`
                : `<div class="anonymous-pill">🟡 Anonymous</div>`;

            return `
                <div class="ticket-card ${stateClass}" onclick="openTicketDetails(${ticket.id})">
                    <div class="ticket-card-header">
                        <span class="dept-tag">${ticket.department}</span>
                        <span class="badge badge-${ticket.severity.toLowerCase().substring(0, 3)}">${ticket.severity}</span>
                    </div>
                    <div class="ticket-card-body">
                        <h3>Patient: ${ticket.patient_id}</h3>
                        <p class="status-summary">Status: <strong>${ticket.status}</strong></p>
                        ${verifiedBadge}
                    </div>
                    <div class="ticket-card-footer">
                        <span>${formatTimeAgo(ticket.created_at)}</span>
                        <div class="sla-timer-pill ${isBreached && !isResolved ? 'breached' : ''} ${isResolved ? 'resolved' : ''}" 
                             data-deadline="${ticket.sla_deadline}" data-id="${ticket.id}">
                            ${isResolved ? '✅' : '⏳'} ${slaDisplay}
                        </div>
                    </div>
                    ${ticket.escalation_level > 0 ? `<div class="ai-reason-pill" style="margin-top:8px">🚨 Escalation L${ticket.escalation_level}</div>` : ''}
                </div>
            `;
        }).join('');
    }

    // --- DETAIL PANEL ---
    window.openTicketDetails = async function (id) {
        currentTicketId = id;
        try {
            const res = await fetch(`${API_BASE_URL}/tickets/${id}`);
            const { data } = await res.json();

            // Reset Panel State
            elements.detailPanel.aiAssigningStatus.classList.remove('hidden');
            elements.detailPanel.autoAssignedDoctorInfo.classList.add('hidden');

            elements.detailPanel.id.textContent = `#TICKET-HID-${data.id}`;
            elements.detailPanel.dept.textContent = data.department;
            elements.detailPanel.status.textContent = data.status;
            elements.detailPanel.status.className = `status-badge status-${data.status.toLowerCase().replace(' ', '-')}`;
            elements.detailPanel.severity.textContent = data.severity;
            elements.detailPanel.severity.className = `severity-badge badge-${data.severity.toLowerCase().substring(0, 3)}`;

            elements.detailPanel.patientId.textContent = data.patient_id;
            elements.detailPanel.sentiment.textContent = data.sentiment;
            elements.detailPanel.received.textContent = new Date(data.created_at).toLocaleString();
            elements.detailPanel.feedbackText.textContent = `"${data.feedback_text}"`;
            elements.detailPanel.aiResponseDraft.value = data.ai_suggested_response || '';

            renderTimeline(data.status_history);
            elements.detailPanel.panel.classList.add('active');
            elements.detailPanel.overlay.classList.add('active');
            updatePanelSLA(data.sla_deadline, data.status);

            // ── Verified Feedback Banner ──────────────────────────────────
            let verifiedBanner = document.getElementById('panelVerifiedBanner');
            if (!verifiedBanner) {
                verifiedBanner = document.createElement('div');
                verifiedBanner.id = 'panelVerifiedBanner';
                verifiedBanner.style.cssText = `
                    background: linear-gradient(135deg,#0d9488,#059669);
                    color:#fff; border-radius:8px; padding:10px 14px;
                    font-size:13px; font-weight:600; margin-bottom:12px;
                    display:flex; gap:8px; align-items:center;
                `;
                const patientSection = document.querySelector('#detailPanel .panel-section');
                if (patientSection) patientSection.prepend(verifiedBanner);
            }
            if (data.is_verified) {
                verifiedBanner.style.background = 'linear-gradient(135deg,#0d9488,#059669)';
                verifiedBanner.style.display = 'flex';
                verifiedBanner.innerHTML = `
                    <span style="font-size:18px">🟢</span>
                    <div>
                        <div>VERIFIED PATIENT</div>
                        <div style="font-weight:400;font-size:12px;opacity:.85">Linked via Completed Appointment &middot; ${data.patient_email || ''}</div>
                    </div>
                `;
            } else {
                verifiedBanner.style.background = '#f1f5f9';
                verifiedBanner.style.color = '#64748b';
                verifiedBanner.style.display = 'flex';
                verifiedBanner.innerHTML = `
                    <span style="font-size:18px">🟡</span>
                    <div>
                        <div>ANONYMOUS FEEDBACK</div>
                        <div style="font-weight:400;font-size:12px;opacity:.85">No completed appointment found / Not verified</div>
                    </div>
                `;
            }

            // ── Staff Assignment: use data embedded in ticket (no secondary fetch) ─
            setTimeout(() => {
                if (data.assigned_staff_info) {
                    displayAssignedDoctor(data.assigned_staff_info);
                } else if (data.assigned_staff && data.assigned_staff !== 'Unassigned') {
                    // Fallback: show minimal card from name string
                    displayAssignedDoctor({
                        name: data.assigned_staff,
                        designation: 'Staff',
                        active_tickets: 0,
                        avg_res_time: 0,
                        performance_rating: 0,
                        load_pct: 0,
                        ai_score: 0
                    });
                } else {
                    elements.detailPanel.aiAssigningStatus.innerHTML = '⚠️ No doctor assigned yet – ticket is in open queue.';
                }
            }, 800);

            if (data.status === 'Resolved') {
                document.getElementById('aiResponseSection').style.display = 'none';
                document.getElementById('assignmentSection').style.display = 'none';
                document.getElementById('resolutionSection').style.display = 'none';
            } else {
                document.getElementById('aiResponseSection').style.display = 'block';
                document.getElementById('assignmentSection').style.display = 'block';
                document.getElementById('resolutionSection').style.display = 'block';
            }

        } catch (error) {
            console.error('Error fetching ticket details:', error);
            showToast('Could not load ticket details', 'error');
        }
    };

    function displayAssignedDoctor(staff) {
        elements.detailPanel.aiAssigningStatus.classList.add('hidden');
        elements.detailPanel.autoAssignedDoctorInfo.classList.remove('hidden');

        const loadColor = staff.load_pct <= 40 ? 'fill-low' : (staff.load_pct <= 70 ? 'fill-med' : 'fill-high');

        elements.detailPanel.autoAssignedDoctorInfo.innerHTML = `
            <div class="auto-staff-header">
                <div>
                    <span class="auto-staff-name">${staff.name} 🤖 AI Choice</span>
                    <span class="auto-staff-dept">${staff.designation}</span>
                </div>
            </div>
            <div class="load-meter-bg">
                <div class="load-meter-fill ${loadColor}" style="width: ${staff.load_pct}%"></div>
            </div>
            <div class="auto-staff-metrics">
                <div class="metric-mini">
                    <span class="metric-mini-label">Current Load</span>
                    <span class="metric-mini-value">${staff.active_tickets}/10 Tasks</span>
                </div>
                <div class="metric-mini">
                    <span class="metric-mini-label">Success Rate</span>
                    <span class="metric-mini-value">${staff.performance_rating}/5.0</span>
                </div>
                <div class="metric-mini">
                    <span class="metric-mini-label">Avg Res Time</span>
                    <span class="metric-mini-value">${staff.avg_res_time}m</span>
                </div>
            </div>
        `;
    }

    async function handleResolution() {
        try {
            const res = await fetch(`${API_BASE_URL}/tickets/${currentTicketId}/resolve`, { method: 'POST' });
            if (res.ok) {
                showToast('Ticket Resolved & Closed');
                closeDetailPanel();
                loadDashboardState();
            }
        } catch (e) { showToast('Resolution failed', 'error'); }
    }

    async function handleRegenerateResponse() {
        elements.detailPanel.aiResponseDraft.value = "Regenerating draft...";
        try {
            const res = await fetch(`${API_BASE_URL}/tickets/${currentTicketId}/regenerate-response`, { method: 'POST' });
            const { data } = await res.json();
            elements.detailPanel.aiResponseDraft.value = data.suggestion;
        } catch (e) { showToast('Regeneration failed', 'error'); }
    }

    async function handleApproveResponse() {
        const content = elements.detailPanel.aiResponseDraft.value;
        try {
            await fetch(`${API_BASE_URL}/tickets/${currentTicketId}/approve-response`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ response_content: content })
            });
            showToast('AI Response Sent Successfully');
        } catch (e) { showToast('Approval failed', 'error'); }
    }

    function renderTimeline(history) {
        elements.detailPanel.history.innerHTML = history.reverse().map(item => `
            <div class="timeline-item">
                <span class="tl-time">${new Date(item.timestamp).toLocaleString()}</span>
                <span class="tl-text">${item.action}</span>
            </div>
        `).join('');
    }

    function closeDetailPanel() {
        elements.detailPanel.panel.classList.remove('active');
        elements.detailPanel.overlay.classList.remove('active');
        currentTicketId = null;
    }

    function switchView(viewName) {
        Object.values(elements.views).forEach(v => { if (v) v.classList.add('hidden'); });
        if (viewName === 'analytics') {
            elements.views.analyticsView.classList.remove('hidden');
            renderAnalytics();
        } else if (viewName === 'heatmap') {
            elements.views.heatmapView.classList.remove('hidden');
            renderHeatmap();
        } else if (viewName === 'appointments') {
            elements.views.appointmentsView.classList.remove('hidden');
            loadAppointments();
        } else {
            elements.views.ticketView.classList.remove('hidden');
        }
    }

    async function renderAnalytics() {
        try {
            const res = await fetch(`${API_BASE_URL}/analytics/performance`);
            const { data } = await res.json();
            Plotly.newPlot('deptComparisonChart', [{
                x: data.map(d => d.department),
                y: data.map(d => d.totalTickets),
                type: 'bar',
                marker: { color: '#2563eb' }
            }], { height: 350 });
        } catch (e) { console.error('Analytics Error:', e); }
    }

    async function renderHeatmap() {
        const res = await fetch(`${API_BASE_URL}/analytics/heatmap`);
        const { data } = await res.json();
        const depts = [...new Set(data.map(d => d.department))];
        const hours = Array.from({ length: 24 }, (_, i) => i);
        const z = depts.map(d => hours.map(h => {
            const found = data.find(item => item.department === d && item.hour === h);
            return found ? found.count : 0;
        }));
        Plotly.newPlot('complaintHeatmap', [{
            x: hours.map(h => h + ":00"),
            y: depts, z: z, type: 'heatmap', colorscale: [['0.0', '#f8fafc'], ['1.0', '#000000']]
        }], { height: 450 });
    }

    async function loadAppointments() {
        const body = document.getElementById('appointmentsListBody');
        if (!body) return;
        body.innerHTML = '<tr><td colspan="7" class="loading-state"><div class="spinner"></div><p>Fetching appointments…</p></td></tr>';
        try {
            const res = await fetch(`${API_BASE_URL}/analytics/appointments`);
            const json = await res.json();
            const rows = json.data || [];

            // Summary badges
            const counts = { Scheduled: 0, 'In Progress': 0, Completed: 0, Cancelled: 0 };
            rows.forEach(a => { if (counts[a.status] !== undefined) counts[a.status]++; });
            const badgesEl = document.getElementById('apptSummaryBadges');
            if (badgesEl) {
                const colors = { Scheduled: '#3b82f6', 'In Progress': '#f59e0b', Completed: '#10b981', Cancelled: '#ef4444' };
                badgesEl.innerHTML = Object.entries(counts).map(([s, c]) =>
                    `<span style="background:${colors[s]};color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700">${s} (${c})</span>`
                ).join('');
            }

            if (!rows.length) {
                body.innerHTML = `<tr><td colspan="7" class="empty-state">No appointments yet.</td></tr>`;
                return;
            }

            const STATUS_COLORS = {
                'Scheduled': '#3b82f6',
                'In Progress': '#f59e0b',
                'Completed': '#10b981',
                'Cancelled': '#ef4444'
            };

            body.innerHTML = rows.map(a => {
                const isCompleted = a.status === 'Completed';
                const opts = ['Scheduled', 'In Progress', 'Completed', 'Cancelled']
                    .map(s => `<option value="${s}"${s === a.status ? ' selected' : ''}>${s}</option>`).join('');

                return `
                <tr id="appt-row-${a.id}" data-status="${a.status}">
                    <td><span class="appt-id-list">#${String(a.id).padStart(4, '0')}</span></td>
                    <td>
                        <div style="font-weight:700;color:#1e293b">${a.patient_name}</div>
                        <div style="font-size:11px;color:#64748b">${a.patient_email}</div>
                    </td>
                    <td><span class="list-dept-tag">${a.department}</span></td>
                    <td style="font-size:13px">${a.doctor || '<em style="color:#cbd5e1">Pending</em>'}</td>
                    <td>
                        <div style="font-weight:600">${a.appointment_date}</div>
                        <div style="font-size:12px;color:#64748b">${a.time_slot}</div>
                    </td>
                    <td>
                        <div style="display:flex;align-items:center;gap:10px">
                             <div class="status-indicator" style="background:${STATUS_COLORS[a.status]}"></div>
                             <select class="appt-list-dropdown" onchange="updateApptStatus(${a.id}, this.value, this)">
                                ${opts}
                             </select>
                        </div>
                    </td>
                    <td>
                        ${isCompleted
                        ? '<span class="verified-unlocked">✅ Verified Eligible</span>'
                        : '<span class="verified-locked">🔒 Not Verified</span>'}
                    </td>
                </tr>`;
            }).join('');

        } catch (e) {
            body.innerHTML = `<tr><td colspan="7" class="empty-state" style="color:#ef4444">⚠️ Error loading data</td></tr>`;
        }
    }

    window.updateApptStatus = async function (apptId, newStatus, selectEl) {
        const row = document.getElementById(`appt-row-${apptId}`);
        const origValue = row ? row.dataset.status : newStatus;
        if (selectEl) selectEl.disabled = true;

        try {
            const res = await fetch(`${API_BASE_URL}/admin/appointments/${apptId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
            const json = await res.json();
            if (json.status !== 'success') throw new Error(json.message || 'Update failed');

            showToast(`Appointment #${apptId} → ${newStatus}`, 'success');
            // Reload the cards to reflect new state (completed_at, verified banner etc.)
            loadAppointments();
        } catch (err) {
            showToast(`Failed to update: ${err.message}`, 'error');
            if (selectEl) { selectEl.value = origValue; selectEl.disabled = false; }
        }
    };



    function startSLAUpdates() {
        if (slaTimerInterval) clearInterval(slaTimerInterval);
        slaTimerInterval = setInterval(() => {
            document.querySelectorAll('.sla-timer-pill').forEach(pill => {
                if (pill.classList.contains('resolved')) return;
                const deadline = pill.getAttribute('data-deadline');
                pill.innerHTML = `⏳ ${getSLAStatus(deadline)}`;
            });
        }, 1000);
    }

    function updatePanelSLA(deadline, status) {
        const isResolved = status === 'Resolved';
        const isBreached = new Date(deadline) < new Date();
        if (isResolved) {
            elements.detailPanel.countdown.textContent = '✅ COMPLETED';
            elements.detailPanel.countdown.style.color = 'var(--success)';
        } else if (isBreached) {
            elements.detailPanel.countdown.textContent = '⚠️ BREACHED';
            elements.detailPanel.countdown.style.color = '#000000';
        } else {
            elements.detailPanel.countdown.textContent = getSLAStatus(deadline);
            elements.detailPanel.countdown.style.color = 'var(--danger)';
        }
    }

    function getSLAStatus(deadlineStr) {
        const diff = new Date(deadlineStr) - new Date();
        if (diff <= 0) return "BREACHED";
        const h = Math.floor(diff / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    function formatTimeAgo(dateStr) {
        const diff = Math.floor((new Date() - new Date(dateStr)) / 60000);
        return diff < 1 ? 'Just now' : (diff < 60 ? `${diff}m ago` : `${Math.floor(diff / 60)}h ago`);
    }

    function setupPolling() {
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(loadDashboardState, REFRESH_INTERVAL);
    }

    function updateLastSyncTime() {
        elements.sidebar.lastUpdate.textContent = new Date().toLocaleTimeString();
    }

    function showLoading(show) {
        elements.ticketGrid.style.opacity = show ? '0.6' : '1';
    }

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.getElementById('toastContainer').appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    init();
});
