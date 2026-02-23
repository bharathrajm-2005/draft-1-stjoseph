/**
 * AUREVIA HOSPITAL INCIDENT INTELLIGENCE
 * FULLY AUTOMATED SMART ASSIGNMENT SYSTEM
 */

document.addEventListener('DOMContentLoaded', () => {
    // Configuration & State
    const API_BASE_URL = '/api';
    const REFRESH_INTERVAL = 10000; // 10 seconds — catches staff resolutions quickly
    let activeTickets = [];
    let emergencyRequests = []; // Cached for driver-assignment cross-ref
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
            appts: document.getElementById('metricAppts'),
            verified: document.getElementById('metricVerified'),
        },
        sidebar: {
            deptFilter: document.getElementById('filterDept'),
            sentimentFilter: document.getElementById('filterSentiment'),
            statusFilter: document.getElementById('filterStatus'),
            viewAnalytics: document.getElementById('showAnalyticsBtn'),
            viewAppointments: document.getElementById('showAppointmentsBtn'),
            viewEmergency: document.getElementById('showEmergencyBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            lastUpdate: document.getElementById('lastUpdate')
        },
        views: {
            ticketView: document.querySelector('.ticket-view'),
            analyticsView: document.getElementById('analyticsSection'),
            appointmentsView: document.getElementById('appointmentsSection'),
            emergencyView: document.getElementById('emergencySection')
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
        if (elements.sidebar.viewAppointments)
            elements.sidebar.viewAppointments.addEventListener('click', () => switchView('appointments'));

        if (elements.sidebar.viewEmergency)
            elements.sidebar.viewEmergency.addEventListener('click', () => switchView('emergency'));

        elements.sidebar.refreshBtn.addEventListener('click', loadDashboardState);

        const closeAnalytics = document.getElementById('closeAnalytics');
        const closeAppointments = document.getElementById('closeAppointments');
        const closeEmergency = document.getElementById('closeEmergency');

        if (closeAnalytics) closeAnalytics.addEventListener('click', () => switchView('tickets'));
        if (closeAppointments) closeAppointments.addEventListener('click', () => switchView('tickets'));
        if (closeEmergency) closeEmergency.addEventListener('click', () => switchView('tickets'));

        elements.detailPanel.close.addEventListener('click', closeDetailPanel);
        elements.detailPanel.overlay.addEventListener('click', closeDetailPanel);
        elements.detailPanel.resolveBtn.addEventListener('click', handleResolution);
        elements.detailPanel.regenerateBtn.addEventListener('click', handleRegenerateResponse);
        elements.detailPanel.approveResponseBtn.addEventListener('click', handleApproveResponse);
    }

    // --- DATA LOADING ---
    async function loadDashboardState() {
        await Promise.all([
            loadMetrics(),
            loadTickets(),
            loadSOSMonitor(),
            loadAmbulanceFleet()
        ]);
        updateLastSyncTime();
    }

    async function loadMetrics() {
        try {
            const [statsRes, apptRes, fbRes] = await Promise.all([
                fetch(`${API_BASE_URL}/stats/dashboard`),
                fetch(`${API_BASE_URL}/analytics/appointments`),
                fetch(`${API_BASE_URL}/tickets?status=all`)
            ]);
            const stats = await statsRes.json();
            if (stats.status === 'success') {
                const d = stats.data;
                elements.metrics.active.textContent = d.activeTickets || 0;
                elements.metrics.rating.textContent = (d.averageRating || 0).toFixed(1);
                elements.metrics.critical.textContent = d.criticalCases || 0;
                elements.metrics.wait.textContent = d.waitTimeAlert || 0;
            }
            // Appointments count
            const appts = await apptRes.json();
            if (appts.data && elements.metrics.appts) {
                elements.metrics.appts.textContent = appts.data.length;
            }
            // Verified feedback count
            const fb = await fbRes.json();
            if (fb.data && elements.metrics.verified) {
                const verified = (fb.data || []).filter(t => t.is_verified).length;
                elements.metrics.verified.textContent = verified;
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
            renderAnalyticsDashboard();
        } else if (viewName === 'appointments') {
            elements.views.appointmentsView.classList.remove('hidden');
            loadAppointments();
        } else if (viewName === 'emergency') {
            elements.views.emergencyView.classList.remove('hidden');
            loadSOSMonitor();
            loadAmbulanceFleet();
        } else {
            elements.views.ticketView.classList.remove('hidden');
        }
    }

    // Shared Plotly layout defaults for a clean, modern look
    const CHART_LAYOUT = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Outfit, Inter, sans-serif', size: 12, color: '#475569' },
        margin: { t: 10, b: 40, l: 40, r: 10 },
        showlegend: true,
        legend: { bgcolor: 'transparent', font: { size: 11 } }
    };
    const CHART_CONFIG = { responsive: true, displayModeBar: false };

    async function renderAnalyticsDashboard() {
        // Fire all 5 data fetches in parallel
        const [perfRes, hmRes, trendRes, apptRes, statsRes] = await Promise.all([
            fetch(`${API_BASE_URL}/analytics/performance`).catch(() => null),
            fetch(`${API_BASE_URL}/analytics/heatmap`).catch(() => null),
            fetch(`${API_BASE_URL}/analytics/trend`).catch(() => null),
            fetch(`${API_BASE_URL}/analytics/appointments`).catch(() => null),
            fetch(`${API_BASE_URL}/stats/dashboard`).catch(() => null)
        ]);

        // 1. Department Workload — horizontal grouped bar
        try {
            const perf = await perfRes.json();
            const depts = perf.data || [];
            const names = depts.map(d => d.department);
            const totals = depts.map(d => d.totalTickets);
            const resolved = depts.map(d => Math.round(d.totalTickets * (1 - d.slaBreachPct / 100)));
            Plotly.newPlot('deptComparisonChart', [
                {
                    name: 'Total Tickets', x: totals, y: names, type: 'bar', orientation: 'h',
                    marker: { color: '#6366f1', opacity: 0.85 }
                },
                {
                    name: 'Resolved', x: resolved, y: names, type: 'bar', orientation: 'h',
                    marker: { color: '#10b981', opacity: 0.85 }
                }
            ], {
                ...CHART_LAYOUT, barmode: 'overlay', height: 300,
                xaxis: { gridcolor: '#f1f5f9' },
                yaxis: { automargin: true }
            }, CHART_CONFIG);
        } catch (e) { console.warn('Dept chart error', e); }

        // 2. Sentiment Donut — from stats deptCounts or tickets
        try {
            const stats = await statsRes.json();
            const tickets = activeTickets.length ? activeTickets :
                (await fetch(`${API_BASE_URL}/tickets?status=all`).then(r => r.json()).catch(() => ({ data: [] }))).data || [];
            const sentCounts = { Positive: 0, Neutral: 0, Negative: 0 };
            tickets.forEach(t => { if (sentCounts[t.sentiment] !== undefined) sentCounts[t.sentiment]++; });
            Plotly.newPlot('sentimentDistributionChart', [{
                labels: Object.keys(sentCounts),
                values: Object.values(sentCounts),
                type: 'pie', hole: 0.55,
                pull: [0, 0, 0.08],
                marker: { colors: ['#10b981', '#f59e0b', '#ef4444'] },
                textinfo: 'label+percent',
                textfont: { size: 12 }
            }], { ...CHART_LAYOUT, height: 300, showlegend: false }, CHART_CONFIG);
        } catch (e) { console.warn('Sentiment chart error', e); }

        // 3. Incident Trend — smooth area line
        try {
            const trend = await trendRes.json();
            const td = trend.data || [];
            Plotly.newPlot('trendChart', [{
                x: td.map(d => d.date),
                y: td.map(d => d.count),
                type: 'scatter', mode: 'lines',
                fill: 'tozeroy',
                line: { color: '#6366f1', width: 2.5, shape: 'spline' },
                fillcolor: 'rgba(99,102,241,0.12)',
                name: 'Incidents'
            }], {
                ...CHART_LAYOUT, height: 260,
                xaxis: { showgrid: false, tickangle: -30 },
                yaxis: { gridcolor: '#f1f5f9', rangemode: 'tozero' }
            }, CHART_CONFIG);
        } catch (e) { console.warn('Trend chart error', e); }

        // 4. Complaint Heatmap
        try {
            const hm = await hmRes.json();
            const hmData = hm.data || [];
            const depts2 = [...new Set(hmData.map(d => d.department))];
            const hours = Array.from({ length: 24 }, (_, i) => i);
            const z = depts2.map(d => hours.map(h => {
                const found = hmData.find(item => item.department === d && item.hour === h);
                return found ? found.count : 0;
            }));
            Plotly.newPlot('complaintHeatmap', [{
                x: hours.map(h => `${h}:00`),
                y: depts2, z: z,
                type: 'heatmap',
                colorscale: [[0, '#f0f9ff'], [0.5, '#6366f1'], [1, '#312e81']],
                showscale: true,
                colorbar: { thickness: 12, len: 0.8 }
            }], {
                ...CHART_LAYOUT, height: 300,
                xaxis: { title: 'Hour of Day', tickangle: -45 },
                yaxis: { automargin: true }
            }, CHART_CONFIG);
        } catch (e) { console.warn('Heatmap error', e); }

        // 5. Appointment Status Donut
        try {
            const appts = await apptRes.json();
            const apptData = appts.data || [];
            const counts = { Scheduled: 0, 'In Progress': 0, Completed: 0, Cancelled: 0 };
            apptData.forEach(a => { if (counts[a.status] !== undefined) counts[a.status]++; });
            Plotly.newPlot('apptStatusChart', [{
                labels: Object.keys(counts),
                values: Object.values(counts),
                type: 'pie', hole: 0.55,
                marker: { colors: ['#3b82f6', '#f59e0b', '#10b981', '#ef4444'] },
                textinfo: 'label+value',
                textfont: { size: 12 }
            }], { ...CHART_LAYOUT, height: 300, showlegend: false }, CHART_CONFIG);
        } catch (e) { console.warn('Appt chart error', e); }
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

    // --- SOS MONITOR & FLEET (RESTRUCTURED) ---
    async function loadSOSMonitor() {
        const container = document.getElementById('sosCardsContainer');
        const countEl = document.getElementById('activeSosCount');
        if (!container) return;

        try {
            const res = await fetch(`${API_BASE_URL}/admin/emergencies`);
            const json = await res.json();
            const data = json.data || [];

            emergencyRequests = data; // Update cache for fleet list cross-ref

            const activeCount = data.filter(r => r.status !== 'Completed').length;
            if (countEl) countEl.textContent = activeCount;

            if (data.length === 0) {
                container.innerHTML = '<div class="empty-state">No emergency requests found.</div>';
                return;
            }

            container.innerHTML = data.map(r => {
                const statusClass = `status-${r.status.toLowerCase().replace(' ', '-')}`;
                const timeStr = new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const acceptedAt = r.accepted_at ? new Date(r.accepted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
                const completedAt = r.completed_at ? new Date(r.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';

                let driverInfo = r.assigned_driver && r.assigned_driver !== 'N/A'
                    ? `<strong>${r.assigned_driver}</strong>`
                    : '<span class="waiting-text">Waiting for Available Driver...</span>';

                if (r.status === 'Completed') driverInfo = r.assigned_driver || 'N/A';

                return `
                    <div class="sos-card ${statusClass}">
                        <div class="sos-card-header">
                            <span class="sos-id">#SOS-${r.id}</span>
                            <span class="sos-status-badge">${r.status.toUpperCase()}</span>
                        </div>
                        <div class="sos-card-body">
                            <h4>${r.patient_name}</h4>
                            <div class="sos-info-row"><span>📞</span> ${r.phone}</div>
                            <div class="sos-info-row"><span>📍</span> ${r.address || 'GPS Coordinates Only'}</div>
                            <div class="sos-assignment">
                                <strong>Assigned to:</strong> ${driverInfo}
                            </div>
                        </div>
                        <div class="sos-card-footer">
                            <div class="sos-time-stack">
                                <span>Created: ${timeStr}</span>
                                ${r.accepted_at ? `<span>Accepted: ${acceptedAt}</span>` : ''}
                                ${r.completed_at ? `<span>Completed: ${completedAt}</span>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            console.error('SOS Monitor Error', e);
            container.innerHTML = '<div class="empty-state error">Failed to load SOS monitor.</div>';
        }
    }

    async function loadAmbulanceFleet() {
        const list = document.getElementById('driverCardsContainer');
        if (!list) return;

        try {
            const res = await fetch(`${API_BASE_URL}/admin/ambulances`);
            const json = await res.json();
            const data = json.data || [];

            list.innerHTML = data.map(amb => {
                const isBusy = amb.status === 'Busy';
                const statusClass = `status-${amb.status.toLowerCase()}`;

                // Cross-reference with emergencyRequests to find the specific SOS ID
                const activeSOS = emergencyRequests.find(r => r.assigned_driver === amb.driver_name && r.status !== 'Completed');
                const sosDisplayId = activeSOS ? `#SOS-${activeSOS.id}` : (amb.active_dispatch ? `#APP-${amb.active_dispatch.id}` : '#N/A');

                return `
                    <div class="driver-card ${statusClass}">
                        <div class="driver-card-icon">🚑</div>
                        <div class="driver-card-info">
                            <strong>${amb.driver_name}</strong>
                            <span class="veh-num">${amb.vehicle_number}</span>
                            <div class="driver-status-pill">${amb.status.toUpperCase()}</div>
                            ${isBusy ? `
                                <div class="driver-assignment">
                                    🤖 Handling Emergency <span class="sos-link">${sosDisplayId}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            console.error('Fleet Load Error', e);
            list.innerHTML = '<div class="empty-state error">Failed to load drivers.</div>';
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
