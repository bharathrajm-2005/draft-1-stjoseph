/**
 * AUREVIA HOSPITAL STAFF PORTAL
 * Vanilla JS with AJAX Polling
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    const API_BASE_URL = '/api/staff';
    let myTasks = [];
    let currentTaskId = null;
    let slaInterval = null;
    let pollingInterval = null;

    // Elements
    const elements = {
        greeting: document.getElementById('staffGreeting'),
        loadPill: document.getElementById('profileLoad'),
        ratingPill: document.getElementById('profileRating'),
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

        // Polling
        pollingInterval = setInterval(() => {
            loadProfile();
            loadTasks();
        }, 5000); // 5 second polling as requested

        // SLA Updates
        slaInterval = setInterval(updateSLATimers, 1000);
    }

    function setupEventListeners() {
        if (elements.close) elements.close.addEventListener('click', closeTaskPanel);
        if (elements.overlay) elements.overlay.addEventListener('click', closeTaskPanel);
        if (elements.completeBtn) elements.completeBtn.addEventListener('click', handleCompleteTask);

        // Sidebar navigation (just refreshing for now)
        const vTasks = document.getElementById('viewTasksBtn');
        const vPerf = document.getElementById('viewPerfBtn');
        if (vTasks) vTasks.addEventListener('click', () => {
            loadTasks();
            showToast('Task list refreshed');
        });
        if (vPerf) vPerf.addEventListener('click', () => {
            showToast('Performance metrics coming soon!', 'info');
        });
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

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.getElementById('toastContainer').appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    init();
});
