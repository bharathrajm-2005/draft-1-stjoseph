/**
 * CAREAXIS HOSPITAL STAFF PORTAL
 * Vanilla JS with AJAX Polling
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    const API_BASE_URL = '/api/staff';
    let myTasks = [];
    let currentTaskId = null;
    let slaInterval = null;
    let pollingInterval = null;
    let emergencyInterval = null;
    let activeAlertId = null;

    // Elements
    const elements = {
        greeting: document.getElementById('staffGreeting'),
        loadPill: document.getElementById('profileLoad'),
        ratingPill: document.getElementById('profileRating'),
        aiScorePill: document.getElementById('profileAIScore'),
        taskGrid: document.getElementById('staffTaskGrid'),
        taskCount: document.getElementById('taskCount'),
        // Task Panel
        panel: document.getElementById('taskPanel'),
        overlay: document.getElementById('taskOverlay'),
        close: document.getElementById('closeTaskPanel'),
        panelTicketId: document.getElementById('taskTicketId'),
        panelPatientId: document.getElementById('taskPatientId'),
        panelSeverity: document.getElementById('taskSeverity'),
        panelSLA: document.getElementById('taskSLA'),
        panelFeedback: document.getElementById('taskFeedbackBody'),
        panelAI: document.getElementById('taskAISuggestion'),
        notesField: document.getElementById('resolutionNotes'),
        completeBtn: document.getElementById('completeTaskBtn')
    };

    // --- INIT ---
    function init() {
        loadProfile();
        loadTasks();
        setupEventListeners();

        // Polling for tasks & profile
        pollingInterval = setInterval(() => {
            if (activeSection === 'tasks') loadTasks();
            loadProfile();
        }, 5000);

        // Appointment polling (30s, lighter)
        apptPollInterval = setInterval(() => {
            if (activeSection === 'appointments') loadDoctorAppointments();
        }, 30000);

        // Emergency Dispatch Polling (Part 1B)
        emergencyInterval = setInterval(pollEmergencyDispatches, 3000);
        pollEmergencyDispatches();

        // SLA Updates
        slaInterval = setInterval(updateSLATimers, 1000);

        // Start on tasks section
        showSection('tasks');
    }

    // ---- active section tracking ----
    let activeSection = 'tasks'; // 'tasks' | 'appointments' | 'perf'
    let apptPollInterval = null;

    function showSection(section) {
        activeSection = section;
        const sectionTasks = document.getElementById('sectionTasks');
        const sectionAppts = document.getElementById('sectionAppointments');
        const btnTasks = document.getElementById('viewTasksBtn');
        const btnAppts = document.getElementById('viewAppointmentsBtn');
        const btnPerf = document.getElementById('viewPerfBtn');

        // Hide all
        if (sectionTasks) sectionTasks.style.display = 'none';
        if (sectionAppts) sectionAppts.style.display = 'none';

        // Remove active from all nav btns
        [btnTasks, btnAppts, btnPerf].forEach(b => b && b.classList.remove('active'));

        if (section === 'tasks') {
            if (sectionTasks) sectionTasks.style.display = '';
            if (btnTasks) btnTasks.classList.add('active');
        } else if (section === 'appointments') {
            if (sectionAppts) sectionAppts.style.display = '';
            if (btnAppts) btnAppts.classList.add('active');
            loadDoctorAppointments();
        } else {
            if (sectionTasks) sectionTasks.style.display = ''; // fallback
            if (btnPerf) btnPerf.classList.add('active');
            showToast('Performance metrics coming soon!', 'info');
        }
    }

    function setupEventListeners() {
        if (elements.close) elements.close.addEventListener('click', closeTaskPanel);
        if (elements.overlay) elements.overlay.addEventListener('click', closeTaskPanel);
        if (elements.completeBtn) elements.completeBtn.addEventListener('click', handleCompleteTask);

        // Sidebar navigation with section switching
        const vTasks = document.getElementById('viewTasksBtn');
        const vAppts = document.getElementById('viewAppointmentsBtn');
        const vPerf = document.getElementById('viewPerfBtn');
        if (vTasks) vTasks.addEventListener('click', () => showSection('tasks'));
        if (vAppts) vAppts.addEventListener('click', () => showSection('appointments'));
        if (vPerf) vPerf.addEventListener('click', () => showSection('perf'));

        // Driver Emergency Actions
        const acceptBtn = document.getElementById('acceptTripBtn');
        const completeBtn = document.getElementById('completeTripBtn');
        const miniCompleteBtn = document.getElementById('miniCompleteBtn');

        if (acceptBtn) acceptBtn.onclick = () => handleTripAction('accept');
        if (completeBtn) completeBtn.onclick = () => handleTripAction('complete');
        if (miniCompleteBtn) miniCompleteBtn.onclick = () => handleTripAction('complete');
    }

    // --- DATA FETCHING ---
    async function loadProfile() {
        try {
            const res = await fetch(`${API_BASE_URL}/profile`);
            if (res.status === 403 || res.status === 401) {
                window.location.href = '/login';
                return;
            }
            const json = await res.json();
            if (json.status !== 'success' || !json.data) return;
            const data = json.data;

            elements.greeting.textContent = `Welcome back, ${data.name}`;
            elements.loadPill.textContent = `${data.load_pct ?? '--'}%`;
            elements.ratingPill.textContent = `${data.success_rate ?? '--'}/5.0`;

            const aiScore = data.ai_performance_score;
            if (elements.aiScorePill) {
                elements.aiScorePill.textContent = (aiScore !== null && aiScore !== undefined) ? aiScore : '—';
                // Optional: color by score
                if (aiScore >= 80) elements.aiScorePill.style.color = '#10b981';
                else if (aiScore >= 50) elements.aiScorePill.style.color = '#f59e0b';
                else if (aiScore > 0) elements.aiScorePill.style.color = '#ef4444';
            }

            // Color load pill by workload
            const loadVal = data.load_pct || 0;
            elements.loadPill.style.color = loadVal > 70 ? '#ef4444' : (loadVal > 40 ? '#f59e0b' : '#10b981');
        } catch (e) { console.error('Profile Load Error', e); }
    }

    async function loadTasks() {
        try {
            const res = await fetch(`${API_BASE_URL}/tasks`);
            if (res.status === 403 || res.status === 401) {
                window.location.href = '/login';
                return;
            }
            const json = await res.json();
            if (json.status !== 'success' || !json.data) {
                console.error('Task Load Error:', json.message);
                return;
            }
            myTasks = json.data;
            renderTasks();
            elements.taskCount.textContent = `${myTasks.length} Active`;
        } catch (e) { console.error('Task Load Error', e); }
    }

    // --- RENDERING ---
    function renderTasks() {
        if (myTasks.length === 0) {
            elements.taskGrid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1; text-align: center; padding: 40px; color: #64748b;">
                    <h3>All caught up! 🎉</h3>
                    <p>New recovery tasks will appear here automatically.</p>
                </div>
            `;
            return;
        }

        elements.taskGrid.innerHTML = myTasks.map(task => {
            const isBreached = new Date(task.sla_deadline) < new Date();
            const priorityClass = `priority-${task.severity.toLowerCase()}`;

            return `
                <div class="staff-task-card ${priorityClass} ${isBreached ? 'breached' : ''}" data-id="${task.id}">
                    <div class="task-card-header">
                        <span class="task-patient-id">PATIENT: ${task.patient_id}</span>
                        <span class="badge badge-${task.severity.toLowerCase().substring(0, 3)}">${task.severity}</span>
                    </div>
                    <p class="task-preview">${task.feedback_text}</p>
                    <div class="task-card-footer">
                        <span class="task-sla-timer ${isBreached ? 'breached' : ''}" data-deadline="${task.sla_deadline}">
                            ${getSLAString(task.sla_deadline)}
                        </span>
                        <button class="btn-text">Open Case →</button>
                    </div>
                </div>
            `;
        }).join('');

        // Add event listeners to NEWLY rendered cards
        document.querySelectorAll('.staff-task-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.getAttribute('data-id');
                window.openTask(parseInt(id));
            });
        });
    }

    // --- UI ACTIONS ---
    window.openTask = function (id) {
        const task = myTasks.find(t => t.id === id);
        if (!task) return;

        currentTaskId = id;
        elements.panelTicketId.textContent = `#CASE-HID-${task.id}`;
        elements.panelPatientId.textContent = `Patient: ${task.patient_id}`;
        elements.panelSeverity.textContent = task.severity;
        elements.panelSeverity.className = `severity-badge badge-${task.severity.toLowerCase().substring(0, 3)}`;
        elements.panelFeedback.textContent = `"${task.feedback_text}"`;
        elements.panelAI.textContent = task.ai_suggestion || "AI is still processing a response suggestion...";

        elements.panel.classList.add('active');
        elements.overlay.classList.add('active');
        elements.notesField.value = '';

        updatePanelSLA(task.sla_deadline);
    };

    function closeTaskPanel() {
        elements.panel.classList.remove('active');
        elements.overlay.classList.remove('active');
        currentTaskId = null;
    }

    async function handleCompleteTask() {
        if (!currentTaskId) {
            showToast('No task selected.', 'error');
            return;
        }
        const notes = elements.notesField.value.trim();
        if (!notes) {
            showToast('Please add resolution notes before marking as resolved.', 'error');
            return;
        }

        elements.completeBtn.disabled = true;
        elements.completeBtn.textContent = '⏳ Processing...';

        try {
            const res = await fetch(`${API_BASE_URL}/complete/${currentTaskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes: notes })
            });

            const json = await res.json();

            if (res.ok && json.status === 'success') {
                showToast('✅ Case Resolved! Dashboard updated.');
                closeTaskPanel();
                // Immediately remove resolved task from local state
                myTasks = myTasks.filter(t => t.id !== currentTaskId);
                renderTasks();
                elements.taskCount.textContent = `${myTasks.length} Active`;
                // Also refresh profile metrics
                loadProfile();
            } else {
                const errMsg = json.message || `Server error (${res.status})`;
                console.error('Complete Task Error:', errMsg);
                showToast(`Error: ${errMsg}`, 'error');
            }
        } catch (e) {
            console.error('Connection error:', e);
            showToast('Connection error. Please try again.', 'error');
        } finally {
            elements.completeBtn.disabled = false;
            elements.completeBtn.textContent = 'MARK AS RESOLVED';
        }
    }

    // --- 🚨 EMERGENCY DRIVER WORKFLOW ---
    async function pollEmergencyDispatches() {
        try {
            const res = await fetch('/api/driver/emergency-status');
            if (!res.ok) return;
            const json = await res.json();

            if (json.status === 'success' && json.data) {
                const alert = json.data;
                activeAlertId = alert.id;
                updateEmergencyOverlay(alert);
            } else {
                // No active mission for this driver
                if (activeAlertId) closeEmergencyOverlay();
                activeAlertId = null;
            }
        } catch (e) {
            console.error('SOS Poll Error', e);
        }
    }

    function updateEmergencyOverlay(alert) {
        const overlay = document.getElementById('emergencyAlertOverlay');
        const miniWidget = document.getElementById('minimizedSosWidget');
        const audio = document.getElementById('emergencyAlarm');

        document.getElementById('alertPatientName').textContent = alert.patient_name;
        document.getElementById('alertPhone').textContent = `☎️ ${alert.phone}`;
        document.getElementById('alertLocation').textContent = alert.address;
        document.getElementById('miniPatientName').textContent = alert.patient_name;

        // Maps Link
        const mapContainer = document.getElementById('alertMapLinkContainer');
        const mapLink = document.getElementById('alertMapLink');
        if (alert.maps_link) {
            mapLink.href = alert.maps_link;
            mapContainer.classList.remove('hidden');
        } else {
            mapContainer.classList.add('hidden');
        }

        const sevBadge = document.getElementById('alertSeverity');
        if (sevBadge) sevBadge.textContent = alert.status.toUpperCase();

        const timeBadge = document.getElementById('alertTime');
        if (timeBadge && alert.created_at) {
            timeBadge.textContent = `Reported: ${formatTimeStack(alert.created_at)}`;
        }

        // ETA Badge (Phase 2)
        const etaContainer = document.getElementById('alertETA');
        const etaValue = document.getElementById('alertETAValue');
        if (etaContainer && etaValue) {
            if (alert.eta_minutes) {
                etaValue.textContent = alert.eta_minutes;
                etaContainer.classList.remove('hidden');
            } else {
                etaContainer.classList.add('hidden');
            }
        }

        const acceptBtn = document.getElementById('acceptTripBtn');
        const completeBtn = document.getElementById('completeTripBtn');

        if (alert.status === 'Dispatched') {
            overlay.classList.add('active'); // Use active class as per CSS
            overlay.classList.remove('hidden');
            miniWidget.classList.add('hidden');
            if (acceptBtn) acceptBtn.classList.remove('hidden');
            if (completeBtn) completeBtn.classList.add('hidden');
            if (audio && audio.paused) audio.play().catch(e => console.log('Audio blocked', e));
        } else if (alert.status === 'In Transit') {
            overlay.classList.add('hidden');
            overlay.classList.remove('active');
            miniWidget.classList.remove('hidden');
            miniWidget.classList.add('active');
            if (audio) audio.pause();
        }
    }

    async function handleTripAction(action) {
        if (!activeAlertId) return;

        const btn = action === 'accept' ? document.getElementById('acceptTripBtn') : document.getElementById('completeTripBtn');
        const miniBtn = document.getElementById('miniCompleteBtn');

        const origText = btn ? btn.textContent : '';
        if (btn) {
            btn.disabled = true;
            btn.textContent = action === 'accept' ? 'ACCEPTING...' : 'COMPLETING...';
        }
        if (miniBtn) miniBtn.disabled = true;

        // FIXED: Use the correct emergency ID routes
        const endpoint = `/api/driver/emergency/${action}/${activeAlertId}`;

        try {
            const res = await fetch(endpoint, { method: 'POST' });
            const json = await res.json();

            if (json.status === 'success') {
                showToast(`✅ Mission ${action === 'accept' ? 'Accepted' : 'Completed'}!`, 'success');
                if (action === 'complete') {
                    closeEmergencyOverlay();
                    activeAlertId = null;
                }
                pollEmergencyDispatches();
            } else {
                showToast(json.message || "Action failed", 'error');
            }
        } catch (e) {
            showToast("Network error during mission update", 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = origText;
            }
            if (miniBtn) miniBtn.disabled = false;
        }
    }

    function closeEmergencyOverlay() {
        const overlay = document.getElementById('emergencyAlertOverlay');
        const miniWidget = document.getElementById('minimizedSosWidget');
        const audio = document.getElementById('emergencyAlarm');

        if (overlay) {
            overlay.classList.add('hidden');
            overlay.classList.remove('active');
        }
        if (miniWidget) {
            miniWidget.classList.add('hidden');
            miniWidget.classList.remove('active');
        }
        if (audio) {
            audio.pause();
            audio.currentTime = 0;
        }
        activeAlertId = null;
    }

    // --- UTILS ---
    function updateSLATimers() {
        document.querySelectorAll('.task-sla-timer').forEach(timer => {
            const deadline = timer.getAttribute('data-deadline');
            const str = getSLAString(deadline);
            timer.textContent = str;
            if (str === "BREACHED") timer.classList.add('breached');
        });

        if (currentTaskId) {
            const task = myTasks.find(t => t.id === currentTaskId);
            if (task) updatePanelSLA(task.sla_deadline);
        }
    }

    function updatePanelSLA(deadline) {
        elements.panelSLA.textContent = getSLAString(deadline);
        const isBreached = new Date(deadline) < new Date();
        elements.panelSLA.style.color = isBreached ? '#000000' : '#ef4444';
    }

    function getSLAString(deadlineStr) {
        const diff = new Date(deadlineStr) - new Date();
        if (diff <= 0) return "BREACHED";

        const h = Math.floor(diff / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }


    function formatTimeStack(isoString) {
        if (!isoString) return '--';
        const date = new Date(isoString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        const mins = Math.floor(diffInSeconds / 60);
        if (mins < 60) return `${mins}m ago`;
        const hours = Math.floor(mins / 60);
        return `${hours}h ago`;
    }

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        // The HTML has toastContainer, checking both for safety
        const container = document.getElementById('toastContainer') || document.getElementById('toastWrapper');
        if (container) container.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }


    //  DOCTOR APPOINTMENTS MODULE

    let myAppointments = [];

    async function loadDoctorAppointments() {
        const grid = document.getElementById('apptGrid');
        try {
            const res = await fetch('/api/doctor/appointments');
            const json = await res.json();
            if (json.status !== 'success') throw new Error(json.message);
            myAppointments = json.data;
            renderAppointments();
        } catch (e) {
            console.error('Appointment load error', e);
            if (grid) grid.innerHTML = '<div class="empty-state"><p>Could not load appointments.</p></div>';
        }
    }

    function renderAppointments() {
        const grid = document.getElementById('apptGrid');
        const countEl = document.getElementById('apptCount');
        if (!grid) return;
        if (countEl) countEl.textContent = myAppointments.length + ' Total';

        if (myAppointments.length === 0) {
            grid.innerHTML = '<div class="empty-state appt-empty"><div class="empty-icon"></div><h3>No Appointments Yet</h3><p>Your scheduled appointments will appear here once assigned.</p></div>';
            return;
        }

        const statusColor = {
            'Scheduled': { bg: '#eff6ff', text: '#1d4ed8', dot: '#3b82f6' },
            'In Progress': { bg: '#fef9c3', text: '#854d0e', dot: '#f59e0b' },
            'Completed': { bg: '#f0fdf4', text: '#15803d', dot: '#22c55e' }
        };

        grid.innerHTML = myAppointments.map(function (a) {
            const sc = statusColor[a.status] || { bg: '#f1f5f9', text: '#475569', dot: '#94a3b8' };
            const isCompleted = a.status === 'Completed';
            const typeIcon = a.type === 'Emergency' ? '' : (a.type === 'Urgent' ? '' : '');
            const dotSpan = '<span style="width:7px;height:7px;border-radius:50%;background:' + sc.dot + ';display:inline-block;margin-right:4px;vertical-align:middle"></span>';
            const verifiedNote = isCompleted ? '<div class="appt-verified-note"> Completed  Patient eligible for Verified feedback</div>' : '';
            const footerBtn = !isCompleted ? '<div class="appt-card-footer"><button class="btn-complete-appt" onclick="window.completeAppointment(' + a.id + ', this)"> Mark as Completed</button></div>' : '';

            return '<div class="appt-card" data-id="' + a.id + '">' +
                '<div class="appt-card-header">' +
                '<div class="appt-id-row">' +
                '<span class="appt-type-icon">' + typeIcon + '</span>' +
                '<span class="appt-id-label">#APPT-' + String(a.id).padStart(4, '0') + '</span>' +
                '</div>' +
                '<span class="appt-status-badge" style="background:' + sc.bg + ';color:' + sc.text + '">' + dotSpan + a.status + '</span>' +
                '</div>' +
                '<div class="appt-card-body">' +
                '<div class="appt-row"><span class="appt-lbl">Patient</span><span class="appt-val">' + a.patient_name + '</span></div>' +
                '<div class="appt-row"><span class="appt-lbl">Email</span><span class="appt-val appt-email">' + a.patient_email + '</span></div>' +
                '<div class="appt-row"><span class="appt-lbl">Date &amp; Time</span><span class="appt-val">' + a.appointment_date + '  ' + a.time_slot + '</span></div>' +
                '<div class="appt-row"><span class="appt-lbl">Department</span><span class="appt-val">' + a.department + '</span></div>' +
                verifiedNote +
                '</div>' +
                footerBtn +
                '</div>';
        }).join('');
    }

    // Exposed globally so inline onclick inside innerHTML works
    window.completeAppointment = async function (apptId, btn) {
        if (!apptId) return;
        var originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Completing\u2026';

        try {
            var res = await fetch('/api/doctor/appointments/' + apptId + '/complete', { method: 'POST' });
            var json = await res.json();
            if (json.status === 'success') {
                showToast('\u2705 Appointment completed! Patient can now submit verified feedback.', 'success');
                loadDoctorAppointments();
                loadProfile();
            } else {
                showToast(json.message || 'Could not complete appointment.', 'error');
                btn.disabled = false;
                btn.textContent = originalText;
            }
        } catch (e) {
            showToast('Network error. Please try again.', 'error');
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };
    init();
});
