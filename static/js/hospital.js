/**
 * AUREVIA HOSPITAL – HOSPITAL.JS
 * Powers: Appointment Booking, Verified Feedback, Navbar Scroll, Animations
 */

const API = '/api';

/* ================================================================
   NAVBAR – Scroll Shadow & Mobile Toggle
================================================================ */
(function initNavbar() {
    const navbar = document.getElementById('navbar');
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');

    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    });

    if (hamburger) {
        hamburger.addEventListener('click', () => {
            navMenu.classList.toggle('open');
        });
    }

    // Active nav link on scroll
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    const observer = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                navLinks.forEach(l => l.classList.remove('active'));
                const link = document.querySelector(`.nav-link[href="#${e.target.id}"]`);
                if (link) link.classList.add('active');
            }
        });
    }, { threshold: 0.4 });
    sections.forEach(s => observer.observe(s));
})();

/* ================================================================
   HERO PARTICLES
================================================================ */
(function initParticles() {
    const container = document.getElementById('heroParticles');
    if (!container) return;
    const COUNT = 30;
    for (let i = 0; i < COUNT; i++) {
        const el = document.createElement('div');
        const size = Math.random() * 4 + 2;
        const x = Math.random() * 100;
        const y = Math.random() * 100;
        const delay = Math.random() * 6;
        const dur = Math.random() * 10 + 8;
        el.style.cssText = `
            position:absolute; width:${size}px; height:${size}px;
            border-radius:50%; background:rgba(255,255,255,${Math.random() * .3 + .05});
            left:${x}%; top:${y}%; animation:float ${dur}s ${delay}s infinite ease-in-out;
        `;
        container.appendChild(el);
    }
})();

/* ================================================================
   BOOKING FORM
================================================================ */
(function initBooking() {
    const form = document.getElementById('bookingForm');
    if (!form) return;

    const deptSel = document.getElementById('bDept');
    const docSel = document.getElementById('bDoctor');
    const dateInput = document.getElementById('bDate');
    const slotInput = document.getElementById('bSlot');
    const submitBtn = document.getElementById('bookingSubmitBtn');
    const btnText = document.getElementById('bookingBtnText');
    const loader = document.getElementById('bookingLoader');

    // Set minimum date to today
    const today = new Date();
    dateInput.min = today.toISOString().split('T')[0];

    // Load departments from API
    async function loadDepartments() {
        try {
            const res = await fetch(`${API}/appointments/departments`);
            const json = await res.json();
            if (json.status !== 'success') throw new Error(json.message);

            deptSel.innerHTML = '<option value="">Select department…</option>';
            json.data.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = d.name;
                deptSel.appendChild(opt);
            });
        } catch (e) {
            // Fallback: static departments
            deptSel.innerHTML = `
                <option value="">Select department…</option>
                <option value="">Cardiology</option>
                <option value="">Neurology</option>
                <option value="">Orthopedics</option>
                <option value="">Emergency</option>
                <option value="">General Medicine</option>
            `;
            console.warn('Could not load departments from API:', e.message);
        }
    }
    loadDepartments();

    // Load doctors when department changes
    deptSel.addEventListener('change', async () => {
        const deptId = deptSel.value;
        docSel.disabled = true;
        docSel.innerHTML = '<option value="">Loading doctors…</option>';

        if (!deptId) {
            docSel.innerHTML = '<option value="">Select department first</option>';
            return;
        }

        try {
            const res = await fetch(`${API}/appointments/departments/${deptId}/doctors`);
            const json = await res.json();
            docSel.innerHTML = '<option value="">No preference (assign automatically)</option>';
            if (json.data && json.data.length > 0) {
                json.data.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id;
                    opt.textContent = `${d.name} – ${d.designation}`;
                    docSel.appendChild(opt);
                });
                docSel.disabled = false;
            } else {
                docSel.innerHTML = '<option value="">No doctors available (auto-assign)</option>';
            }
        } catch (e) {
            docSel.innerHTML = '<option value="">Could not load doctors</option>';
        }
    });

    // Time slot selection
    document.querySelectorAll('.timeslot').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.timeslot').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            slotInput.value = btn.dataset.slot;
            document.getElementById('bSlotErr').textContent = '';
        });
    });

    // Dept card shortcuts
    document.querySelectorAll('.dept-card[data-dept]').forEach(card => {
        card.addEventListener('click', () => {
            const deptName = card.dataset.dept;
            document.getElementById('booking').scrollIntoView({ behavior: 'smooth' });
            setTimeout(() => {
                const opt = [...deptSel.options].find(o => o.textContent === deptName);
                if (opt) {
                    deptSel.value = opt.value;
                    deptSel.dispatchEvent(new Event('change'));
                }
            }, 600);
        });
    });
    document.querySelectorAll('.doctor-book-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            document.getElementById('booking').scrollIntoView({ behavior: 'smooth' });
        });
    });

    // FORM SUBMIT
    form.addEventListener('submit', async e => {
        e.preventDefault();
        let valid = true;

        const name = document.getElementById('bName').value.trim();
        const email = document.getElementById('bEmail').value.trim();
        const dept = deptSel.value;
        const date = dateInput.value;
        const slot = slotInput.value;

        document.getElementById('bNameErr').textContent = '';
        document.getElementById('bEmailErr').textContent = '';
        document.getElementById('bDeptErr').textContent = '';
        document.getElementById('bDateErr').textContent = '';
        document.getElementById('bSlotErr').textContent = '';

        if (!name) { document.getElementById('bNameErr').textContent = 'Please enter your name'; valid = false; }
        if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { document.getElementById('bEmailErr').textContent = 'Please enter a valid email'; valid = false; }
        if (!dept) { document.getElementById('bDeptErr').textContent = 'Please select a department'; valid = false; }
        if (!date) { document.getElementById('bDateErr').textContent = 'Please select a date'; valid = false; }
        if (!slot) { document.getElementById('bSlotErr').textContent = 'Please select a time slot'; valid = false; }

        if (!valid) return;

        // Submit
        btnText.style.display = 'none';
        loader.style.display = 'inline';
        submitBtn.disabled = true;

        try {
            const res = await fetch(`${API}/appointments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_name: name,
                    patient_email: email,
                    department_id: parseInt(dept),
                    doctor_id: docSel.value ? parseInt(docSel.value) : null,
                    appointment_date: date,
                    time_slot: slot
                })
            });
            const json = await res.json();

            if (res.ok && json.status === 'success') {
                showBookingModal(json.data);
                form.reset();
                document.querySelectorAll('.timeslot').forEach(b => b.classList.remove('selected'));
                slotInput.value = '';
                docSel.disabled = true;
                docSel.innerHTML = '<option value="">Select department first</option>';
            } else {
                alert(json.message || 'Booking failed. Please try again.');
            }
        } catch (err) {
            alert('Connection error. Please check your connection and try again.');
        } finally {
            btnText.style.display = 'inline';
            loader.style.display = 'none';
            submitBtn.disabled = false;
        }
    });

    function showBookingModal(data) {
        const modal = document.getElementById('bookingModal');
        const detailsEl = document.getElementById('bookingConfirmDetails');
        detailsEl.innerHTML = `
            <div class="confirm-row"><span class="clbl">Appointment ID</span><span class="cval">#${String(data.appointment_id).padStart(4, '0')}</span></div>
            <div class="confirm-row"><span class="clbl">Patient</span><span class="cval">${data.patient_name}</span></div>
            <div class="confirm-row"><span class="clbl">Department</span><span class="cval">${data.department}</span></div>
            <div class="confirm-row"><span class="clbl">Doctor</span><span class="cval">${data.doctor}</span></div>
            <div class="confirm-row"><span class="clbl">Date</span><span class="cval">${data.date}</span></div>
            <div class="confirm-row"><span class="clbl">Time</span><span class="cval">${data.time}</span></div>
        `;
        modal.classList.add('open');
    }

    document.getElementById('closeBookingModal').addEventListener('click', () => {
        document.getElementById('bookingModal').classList.remove('open');
    });
    document.getElementById('bookingModal').addEventListener('click', e => {
        if (e.target === e.currentTarget) e.currentTarget.classList.remove('open');
    });
})();

/* ================================================================
   FEEDBACK FORM (Enhanced with Verified Logic)
================================================================ */
(function initFeedback() {
    const form = document.getElementById('feedbackForm');
    if (!form) return;

    let selectedRating = 0;

    // Star rating
    const stars = document.querySelectorAll('.star-btn');
    stars.forEach(star => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.dataset.val);
            document.getElementById('fRating').value = selectedRating;
            document.getElementById('fRatingErr').textContent = '';
            updateStars(selectedRating);
        });
        star.addEventListener('mouseenter', () => updateStars(parseInt(star.dataset.val)));
        star.addEventListener('mouseleave', () => updateStars(selectedRating));
    });

    function updateStars(val) {
        stars.forEach((s, i) => s.classList.toggle('active', i < val));
    }

    // Char counter
    const msgArea = document.getElementById('fMessage');
    const counter = document.getElementById('fCharCount');
    msgArea.addEventListener('input', () => {
        counter.textContent = msgArea.value.length;
        counter.style.color = msgArea.value.length > 450 ? '#ef4444' : '';
    });

    // Submit
    const submitBtn = document.getElementById('feedbackSubmitBtn');
    const btnText = document.getElementById('feedbackBtnText');
    const loader = document.getElementById('feedbackLoader');

    form.addEventListener('submit', async e => {
        e.preventDefault();
        let valid = true;

        const pid = document.getElementById('fPatientId').value.trim();
        const name = document.getElementById('fName').value.trim();
        const email = document.getElementById('fEmail').value.trim();
        const msg = msgArea.value.trim();
        const rat = selectedRating;

        document.getElementById('fPatientIdErr').textContent = '';
        document.getElementById('fRatingErr').textContent = '';
        document.getElementById('fMessageErr').textContent = '';

        if (!pid) { document.getElementById('fPatientIdErr').textContent = 'Patient ID is required'; valid = false; }
        if (!rat) { document.getElementById('fRatingErr').textContent = 'Please select a rating'; valid = false; }
        if (msg.length < 10) { document.getElementById('fMessageErr').textContent = 'Feedback must be at least 10 characters'; valid = false; }

        if (!valid) return;

        btnText.style.display = 'none';
        loader.style.display = 'inline';
        submitBtn.disabled = true;

        try {
            const res = await fetch(`${API}/submit-feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_id: pid,
                    name: name,
                    email: email,
                    feedback_text: msg,
                    rating: rat
                })
            });
            const json = await res.json();

            if (res.ok && json.status === 'success') {
                showFeedbackModal(json.data);
                form.reset();
                selectedRating = 0;
                updateStars(0);
                counter.textContent = '0';
                document.getElementById('verifiedBadge').style.display = 'none';
            } else {
                alert(json.message || 'Submission failed. Please try again.');
            }
        } catch (err) {
            alert('Connection error. Please try again.');
        } finally {
            btnText.style.display = 'inline';
            loader.style.display = 'none';
            submitBtn.disabled = false;
        }
    });

    function showFeedbackModal(data) {
        const modal = document.getElementById('feedbackModal');
        const gridEl = document.getElementById('fModalGrid');
        const verified = data.is_verified;

        const sentColor = { 'Positive': '#10b981', 'Negative': '#ef4444', 'Neutral': '#f59e0b' };
        const sevColor = { 'Critical': '#ef4444', 'High': '#f59e0b', 'Medium': '#3b82f6', 'Normal': '#10b981' };

        gridEl.innerHTML = `
            <div class="fa-cell">
                <div class="fa-label">Sentiment</div>
                <div class="fa-value" style="color:${sentColor[data.sentiment] || '#64748b'}">${data.sentiment || '--'}</div>
            </div>
            <div class="fa-cell">
                <div class="fa-label">Issue Type</div>
                <div class="fa-value">${data.issue_type || '--'}</div>
            </div>
            <div class="fa-cell">
                <div class="fa-label">Severity</div>
                <div class="fa-value" style="color:${sevColor[data.severity] || '#64748b'}">${data.severity || '--'}</div>
            </div>
        `;

        const verifiedNote = document.getElementById('fVerifiedNote');
        verifiedNote.style.display = verified ? 'block' : 'none';

        if (verified && data.linked_doctor) {
            verifiedNote.innerHTML = `🔒 <strong>Verified Feedback</strong> – Linked to your appointment and routed directly to <strong>${data.linked_doctor}</strong>.`;
        }

        modal.classList.add('open');
    }

    document.getElementById('closeFeedbackModal').addEventListener('click', () => {
        document.getElementById('feedbackModal').classList.remove('open');
    });
    document.getElementById('closeFeedbackModalBtn').addEventListener('click', () => {
        document.getElementById('feedbackModal').classList.remove('open');
    });
    document.getElementById('feedbackModal').addEventListener('click', e => {
        if (e.target === e.currentTarget) e.currentTarget.classList.remove('open');
    });
})();

/* ================================================================
   SCROLL REVEAL ANIMATIONS
================================================================ */
(function initScrollReveal() {
    const items = document.querySelectorAll(
        '.about-card, .dept-card, .feature-item, .doctor-card, .testimonial-card, .contact-item'
    );
    const obs = new IntersectionObserver(entries => {
        entries.forEach((e, i) => {
            if (e.isIntersecting) {
                setTimeout(() => {
                    e.target.style.opacity = '1';
                    e.target.style.transform = 'translateY(0)';
                }, i * 80);
                obs.unobserve(e.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    items.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(24px)';
        el.style.transition = 'opacity .5s ease, transform .5s ease';
        obs.observe(el);
    });
})();
