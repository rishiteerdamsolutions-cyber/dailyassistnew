document.addEventListener('DOMContentLoaded', () => {
    const navBtns = document.querySelectorAll('.nav-btn');
    const titleEl = document.getElementById('module-title');
    const runBtn = document.getElementById('run-btn');
    const contentArea = document.getElementById('content-area');

    let currentModule = 'timing';

    const MODULE_TITLES = {
        'timing': 'Chrono-Entropy & Timing Manager',
        'kinematic': 'Kinematic Motion Synthesizer',
        'policy': 'Behavioral Policy & State Engine',
        'linguistic': 'Linguistic Variance & Typo Engine',
        'lifecycle': 'Session & Profile Lifecycle Controller',
        'hardware': 'Hardware-Anchored Jitter'
    };

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentModule = btn.dataset.module;
            titleEl.textContent = MODULE_TITLES[currentModule];
            
            // Reset content area
            contentArea.innerHTML = `
                <div class="empty-state">
                    <div class="pulse-ring"></div>
                    <p>Click "Run Simulation" to execute this module.</p>
                </div>
            `;
        });
    });

    runBtn.addEventListener('click', async () => {
        runBtn.disabled = true;
        runBtn.textContent = 'Running...';
        
        contentArea.innerHTML = `
            <div class="empty-state">
                <div class="pulse-ring" style="animation-duration: 1s;"></div>
                <p>Executing ${MODULE_TITLES[currentModule]}...</p>
            </div>
        `;

        try {
            const response = await fetch(`/api/${currentModule}`);
            const data = await response.json();
            renderResult(currentModule, data);
        } catch (err) {
            contentArea.innerHTML = `<div class="data-view" style="color: var(--danger)">Error: ${err.message}</div>`;
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = 'Run Simulation';
        }
    });

    function renderResult(module, data) {
        let html = '<div class="result-container">';
        
        if (module === 'timing') {
            html += `
                <div class="result-grid">
                    <div class="stat-card">
                        <span class="stat-label">Pool Size</span>
                        <span class="stat-value">${data.pool_size}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Min Latency</span>
                        <span class="stat-value">${data.min_val.toFixed(1)}ms</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Max Latency</span>
                        <span class="stat-value">${data.max_val.toFixed(1)}ms</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Generation Time</span>
                        <span class="stat-value">${data.gen_time_ms.toFixed(1)}ms</span>
                    </div>
                </div>
                <h3 style="margin-bottom: 15px; color: var(--text-secondary);">Sample Values (Beta Distribution)</h3>
                <div class="data-view">${data.sample.map(v => v.toFixed(2) + 'ms').join('\\n')}</div>
            `;
        } else if (module === 'kinematic') {
            html += `
                <div class="result-grid">
                    <div class="stat-card">
                        <span class="stat-label">Distance</span>
                        <span class="stat-value">${data.distance.toFixed(0)}px</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Duration</span>
                        <span class="stat-value">${data.duration_ms.toFixed(0)}ms</span>
                    </div>
                </div>
                <h3 style="margin-bottom: 15px; color: var(--text-secondary);">Bezier Trajectory Points</h3>
                <div class="data-view">${data.trajectory.map(p => `(${p.x.toFixed(1)}, ${p.y.toFixed(1)})`).join(' → ')}</div>
            `;
        } else if (module === 'policy') {
            html += `
                <div class="result-grid">
                    <div class="stat-card">
                        <span class="stat-label">Personality Vector</span>
                        <span class="stat-value" style="font-size: 1.2rem;">${data.personality}</span>
                    </div>
                </div>
                <h3 style="margin-bottom: 15px; color: var(--text-secondary);">Markov Chain State Transitions</h3>
                <div class="data-view">
                    ${data.states.map((s, i) => `[${i+1}] ${s.state.padEnd(15, ' ')} | duration: ${(s.duration_ms/1000).toFixed(1)}s`).join('\\n')}
                </div>
            `;
        } else if (module === 'linguistic') {
            html += `
                <div class="result-grid">
                    <div class="stat-card">
                        <span class="stat-label">Total Duration</span>
                        <span class="stat-value">${(data.total_duration_ms/1000).toFixed(2)}s</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">WPM (Start → End)</span>
                        <span class="stat-value">${data.wpm_start.toFixed(1)} → ${data.wpm_end.toFixed(1)}</span>
                    </div>
                </div>
                <h3 style="margin-bottom: 15px; color: var(--text-secondary);">Keystroke Stream ("${data.text}")</h3>
                <div style="background: rgba(0,0,0,0.3); padding: 20px; border-radius: 12px; line-height: 2;">
            `;
            
            data.events.forEach(e => {
                let displayChar = e.char === ' ' ? '␣' : e.char;
                let classes = 'keystroke';
                if (e.is_typo) classes += ' typo';
                if (e.is_correction) classes += ' correction';
                
                html += `<span class="${classes}" title="${e.delay_ms.toFixed(0)}ms delay">${displayChar}</span>`;
            });
            html += `</div>`;
            
        } else if (module === 'lifecycle') {
            html += `
                <div class="result-grid">
                    <div class="stat-card">
                        <span class="stat-label">Today's Date</span>
                        <span class="stat-value" style="font-size: 1.2rem;">${data.today}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Day Type</span>
                        <span class="stat-value" style="font-size: 1.2rem;">${data.day_type}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Action Allowed</span>
                        <span class="stat-value" style="color: ${data.should_execute ? 'var(--success)' : 'var(--danger)'}">${data.should_execute ? 'YES' : 'NO'}</span>
                    </div>
                </div>
                <h3 style="margin-bottom: 15px; color: var(--text-secondary);">Scheduled Voids (Digital Detox)</h3>
                <div class="data-view">
                    ${data.scheduled_voids.map(v => `● ${v.start} → ${v.end} (${v.duration} days) — ${v.reason}`).join('\\n')}
                </div>
            `;
        } else if (module === 'hardware') {
            if (data.error) {
                html += `<div class="data-view" style="color: var(--danger)">${data.error}</div>`;
            } else {
                html += `
                    <div class="result-grid">
                        <div class="stat-card">
                            <span class="stat-label">Avg Jitter</span>
                            <span class="stat-value">${(data.samples.reduce((a,b)=>a+b.jitter_ms,0)/data.samples.length).toFixed(2)}ms</span>
                        </div>
                    </div>
                    <h3 style="margin-bottom: 15px; color: var(--text-secondary);">Real-Time Hardware Sampling</h3>
                    <div class="data-view">
                        ${data.samples.map((s, i) => `Sample ${i+1}: CPU=${s.cpu_percent}% | RAM=${s.ram_percent}% → Jitter=${s.jitter_ms.toFixed(2)}ms`).join('\\n')}
                    </div>
                `;
            }
        }
        
        html += '</div>';
        contentArea.innerHTML = html;
    }
});
