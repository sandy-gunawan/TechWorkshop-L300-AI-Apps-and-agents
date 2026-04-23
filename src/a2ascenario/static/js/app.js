/* Zava Agent Collaboration Lab — frontend */
(function () {
    'use strict';

    const AGENT_META = {
        product:   { id: 'product',   name: 'ProductAgent',   icon: '📦' },
        marketing: { id: 'marketing', name: 'MarketingAgent', icon: '📣' },
        ranker:    { id: 'ranker',    name: 'RankerAgent',    icon: '🏆' },
        manager:   { id: 'manager',   name: 'ManagerAgent',   icon: '🧠' },
    };

    // -----------------------------------------------------------------
    // Diagram helpers (lines + node states) — same logic as a2a/static
    // -----------------------------------------------------------------
    const LINE_MAP = {
        'a2a-user|a2a-client':       'user-client',
        'a2a-client|a2a-server':     'client-server',
        'a2a-server|a2a-manager':    'server-manager',
        'a2a-manager|a2a-product':   'manager-product',
        'a2a-manager|a2a-marketing': 'manager-marketing',
        'a2a-manager|a2a-ranker':    'manager-ranker',
    };
    const CONNECTIONS = Object.keys(LINE_MAP).map(k => k.split('|'));

    function drawLines() {
        CONNECTIONS.forEach(([aId, bId]) => {
            const key = LINE_MAP[aId + '|' + bId];
            const line = document.getElementById('line-' + key);
            const glow = document.getElementById('glow-' + key);
            const a = document.getElementById(aId);
            const b = document.getElementById(bId);
            if (!line || !a || !b) return;
            const aOn = a.classList.contains('active') || a.classList.contains('done');
            const bOn = b.classList.contains('active') || b.classList.contains('done');
            const isOn = aOn && bOn;
            if (isOn) {
                line.setAttribute('stroke', '#22d3ee');
                line.setAttribute('stroke-width', '2.5');
                line.setAttribute('stroke-opacity', '1');
                line.removeAttribute('stroke-dasharray');
                line.setAttribute('stroke-linecap', 'round');
                if (glow) glow.setAttribute('stroke-opacity', '0.3');
            } else {
                line.setAttribute('stroke', '#818cf8');
                line.setAttribute('stroke-width', '1.5');
                line.setAttribute('stroke-opacity', '0.45');
                line.setAttribute('stroke-dasharray', '6 4');
                line.removeAttribute('stroke-linecap');
                if (glow) glow.setAttribute('stroke-opacity', '0');
            }
        });
    }

    function setNodeStatus(nodeId, status) {
        const n = document.getElementById(nodeId);
        if (!n) return;
        n.classList.remove('active', 'done');
        if (status === 'active') n.classList.add('active');
        else if (status === 'done') n.classList.add('done');
        drawLines();
    }

    function resetDiagram() {
        document.querySelectorAll('.a2a-node').forEach(n => n.classList.remove('active', 'done'));
        drawLines();
    }

    function addFlowEntry(text, type) {
        const log = document.getElementById('a2a-flow');
        if (!log) return;
        const colors = { active: '#22d3ee', done: '#10b981', user: '#a855f7', info: '#94a3b8' };
        const bgs    = { active: '#0e2a3a', done: '#0a2e1f', user: '#1e1b4b', info: '#1f2937' };
        const entry = document.createElement('div');
        entry.style.cssText =
            'padding:3px 6px;margin-bottom:3px;border-radius:4px;border-left:3px solid ' +
            (colors[type] || '#6b7280') + ';background:' + (bgs[type] || '#1f2937');
        const time = new Date().toLocaleTimeString();
        entry.innerHTML = '<span style="color:#6b7280;font-size:0.6rem;">' + time + '</span> ' + escapeHtml(text);
        log.appendChild(entry);
        log.scrollTop = log.scrollHeight;
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c =>
            ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
    }

    // -----------------------------------------------------------------
    // Discussion view rendering
    // -----------------------------------------------------------------
    const els = {
        picker:        document.getElementById('scenario-picker'),
        discussion:    document.getElementById('discussion-area'),
        messages:      document.getElementById('messages'),
        title:         document.getElementById('discussion-title'),
        statusWrap:    document.getElementById('discussion-status'),
        statusText:    document.getElementById('discussion-status-text'),
        statusDot:     document.getElementById('status-dot'),
        topStatusText: document.getElementById('status-text'),
        backBtn:       document.getElementById('back-to-scenarios'),
    };

    function setBusy(busy, label) {
        if (busy) {
            els.statusDot.classList.add('busy');
            els.topStatusText.textContent = label || 'Discussion in progress…';
        } else {
            els.statusDot.classList.remove('busy');
            els.topStatusText.textContent = 'Ready';
        }
    }

    function showDiscussion(scenarioMeta) {
        els.picker.style.display = 'none';
        els.discussion.style.display = 'flex';
        els.messages.innerHTML = '';
        els.title.textContent = scenarioMeta.icon + '  ' + scenarioMeta.title;
        els.statusWrap.classList.remove('done');
        els.statusText.textContent = 'Manager is selecting first speaker…';

        // Show what the user asked (the scenario prompt)
        appendUserPrompt(scenarioMeta.prompt);
        // Show a separator
        appendSectionLabel('🤖 Agent-to-Agent Discussion');
    }

    function showPicker() {
        els.picker.style.display = 'block';
        els.discussion.style.display = 'none';
    }

    function appendRoundDivider(round) {
        const div = document.createElement('div');
        div.className = 'round-divider';
        div.textContent = `— Round ${round} —`;
        els.messages.appendChild(div);
        scrollMessages();
    }

    function appendUserPrompt(prompt) {
        const div = document.createElement('div');
        div.className = 'user-prompt-bubble';
        div.innerHTML = `
            <div class="user-prompt-label">👤 User Request</div>
            <div class="user-prompt-text">${escapeHtml(prompt)}</div>
            <div class="user-prompt-time">${new Date().toLocaleTimeString()}</div>
        `;
        els.messages.appendChild(div);
        scrollMessages();
    }

    function appendSectionLabel(text) {
        const div = document.createElement('div');
        div.className = 'section-label';
        div.innerHTML = text;
        els.messages.appendChild(div);
        scrollMessages();
    }

    function appendFinalResponse(summary) {
        // separator
        appendSectionLabel('👤 Final Response to User');
        const div = document.createElement('div');
        div.className = 'final-response-card';
        div.innerHTML = `
            <div class="final-response-label">📨 Response delivered to user</div>
            <div class="final-response-text">${escapeHtml(summary)}</div>
            <div class="final-response-time">${new Date().toLocaleTimeString()}</div>
        `;
        els.messages.appendChild(div);
        scrollMessages();
    }

    function appendAgentMessage(agentId, agentName, message, round) {
        const meta = AGENT_META[agentId] || { name: agentName, icon: '🤖' };
        const wrap = document.createElement('div');
        wrap.className = 'agent-msg ' + agentId;
        wrap.innerHTML = `
            <div class="agent-avatar">${meta.icon}</div>
            <div class="agent-bubble">
                <div class="agent-header">
                    <span class="agent-name">${escapeHtml(meta.name)}</span>
                    <span class="agent-round-badge">Round ${round}</span>
                </div>
                <div class="agent-text">${escapeHtml(message)}</div>
            </div>
        `;
        els.messages.appendChild(wrap);
        scrollMessages();
    }

    function appendManagerDecision(decision, nextAgent, reason) {
        const div = document.createElement('div');
        div.className = 'manager-decision';
        const icon = decision === 'continue' ? '➡️' : '🏁';
        const nextTxt = nextAgent ? ` → next: <b>${escapeHtml(AGENT_META[nextAgent]?.name || nextAgent)}</b>` : '';
        div.innerHTML = `<span class="md-icon">${icon}</span><b>Manager:</b> ${escapeHtml(decision.toUpperCase())}${nextTxt} <span style="opacity:0.7;">— ${escapeHtml(reason)}</span>`;
        els.messages.appendChild(div);
        scrollMessages();
    }

    function appendConsensus(summary, rounds) {
        const div = document.createElement('div');
        div.className = 'consensus-card';
        div.innerHTML = `
            <div class="consensus-header">
                <i class="fas fa-handshake"></i>
                Consensus Reached
                <span style="font-weight:400; font-size:0.75rem; opacity:0.8; margin-left:auto;">
                    after ${rounds} round${rounds === 1 ? '' : 's'}
                </span>
            </div>
            <div class="consensus-text">${escapeHtml(summary)}</div>
        `;
        els.messages.appendChild(div);
        scrollMessages();

        // Show final response to user
        appendFinalResponse(summary);
    }

    function appendError(message) {
        const div = document.createElement('div');
        div.className = 'consensus-card';
        div.style.border = '1px solid #ef4444';
        div.style.background = 'rgba(239,68,68,0.1)';
        div.innerHTML = `
            <div class="consensus-header" style="color:#ef4444;">
                <i class="fas fa-exclamation-triangle"></i> Discussion Failed
            </div>
            <div class="consensus-text">${escapeHtml(message)}</div>
        `;
        els.messages.appendChild(div);
        scrollMessages();
    }

    function scrollMessages() {
        els.messages.scrollTop = els.messages.scrollHeight;
    }

    // -----------------------------------------------------------------
    // SSE streaming
    // -----------------------------------------------------------------
    let lastRoundDividerShown = -1;

    async function startDiscussion(scenarioId) {
        const meta = window.SCENARIOS[scenarioId];
        if (!meta) return;

        showDiscussion(meta);
        resetDiagram();
        document.getElementById('a2a-flow').innerHTML = '';
        setBusy(true);
        lastRoundDividerShown = -1;

        // Disable scenario buttons while running (in case picker re-shown later)
        document.querySelectorAll('.scenario-card').forEach(b => b.disabled = true);

        let response;
        try {
            response = await fetch((window.BASE_PATH || '') + '/api/discuss/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario: scenarioId }),
            });
        } catch (e) {
            appendError('Network error: ' + e.message);
            finishDiscussion();
            return;
        }

        if (!response.ok || !response.body) {
            appendError('Server error: ' + response.status);
            finishDiscussion();
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const payload = line.slice(6).trim();
                    if (payload === '[DONE]') continue;
                    let event;
                    try { event = JSON.parse(payload); }
                    catch { continue; }
                    handleEvent(event);
                }
            }
        } catch (e) {
            appendError('Stream interrupted: ' + e.message);
        } finally {
            finishDiscussion();
        }
    }

    function handleEvent(event) {
        switch (event.type) {
            case 'trace': {
                const nodeId = 'a2a-' + event.agent;
                setNodeStatus(nodeId, event.status);
                addFlowEntry(event.msg || '', event.status || 'info');
                break;
            }
            case 'round_start': {
                if (event.round !== lastRoundDividerShown) {
                    appendRoundDivider(event.round);
                    lastRoundDividerShown = event.round;
                }
                els.statusText.textContent = `Round ${event.round} of ${window.MAX_ROUNDS}…`;
                break;
            }
            case 'agent_turn': {
                appendAgentMessage(event.agent, event.agent_name, event.message, event.round);
                break;
            }
            case 'manager_decision': {
                appendManagerDecision(event.decision, event.next_agent, event.reason);
                break;
            }
            case 'consensus': {
                appendConsensus(event.summary, event.rounds);
                els.statusWrap.classList.add('done');
                els.statusText.textContent = `Concluded after ${event.rounds} round${event.rounds === 1 ? '' : 's'}`;
                break;
            }
            case 'error': {
                appendError(event.message || 'Unknown error');
                break;
            }
        }
    }

    function finishDiscussion() {
        setBusy(false);
        document.querySelectorAll('.scenario-card').forEach(b => b.disabled = false);
    }

    // -----------------------------------------------------------------
    // Wire up scenario cards + back button
    // -----------------------------------------------------------------
    document.querySelectorAll('.scenario-card').forEach(card => {
        card.addEventListener('click', () => {
            const sid = card.getAttribute('data-scenario');
            startDiscussion(sid);
        });
    });

    els.backBtn.addEventListener('click', showPicker);

    // Initial draw + redraw on resize
    setTimeout(drawLines, 200);
    window.addEventListener('resize', drawLines);

    // Health check
    fetch((window.BASE_PATH || '') + '/health').catch(() => {
        els.statusDot.classList.add('error');
        els.topStatusText.textContent = 'Disconnected';
    });
})();
