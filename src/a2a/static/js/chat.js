class ProductManagementAgentChat {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.isTyping = false;
        this.messageHistory = [];
        
        this.initializeElements();
        this.attachEventListeners();
        this.updateStatus('connected');
        this.autoResizeTextarea();
    }

    initializeElements() {
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.messagesContainer = document.getElementById('messages');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.welcomeMessage = document.getElementById('welcome-message');
        this.statusIndicator = document.getElementById('status-indicator');
        this.statusText = document.getElementById('status-text');
        this.charCount = document.getElementById('char-count');
        this.newConversationBtn = document.getElementById('new-conversation-btn');
    }

    attachEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // New conversation button click
        this.newConversationBtn.addEventListener('click', () => this.startNewConversation());
        
        // Enter key to send (Shift+Enter for new line)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Input validation and character counter
        this.messageInput.addEventListener('input', () => {
            this.updateSendButton();
            this.updateCharCounter();
            this.autoResizeTextarea();
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('paste', () => {
            setTimeout(() => this.autoResizeTextarea(), 0);
        });
    }

    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    startNewConversation() {
        // Generate new session ID
        this.sessionId = this.generateSessionId();
        
        // Clear message history
        this.messageHistory = [];
        
        // Clear chat messages
        this.messagesContainer.innerHTML = '';
        
        // Show welcome message again
        this.welcomeMessage.style.display = 'block';
        
        // Clear input
        this.messageInput.value = '';
        this.updateSendButton();
        this.updateCharCounter();
        this.autoResizeTextarea();
        
        // Hide typing indicator
        this.typingIndicator.style.display = 'none';
        this.isTyping = false;
        
        console.log('Started new conversation with session ID:', this.sessionId);
    }

    updateStatus(status) {
        const statusMap = {
            'connecting': { text: 'Connecting...', class: '' },
            'connected': { text: 'Online', class: 'connected' },
            'error': { text: 'Connection Error', class: 'error' }
        };
        
        const statusInfo = statusMap[status] || statusMap['connecting'];
        this.statusText.textContent = statusInfo.text;
        this.statusIndicator.className = `status-indicator ${statusInfo.class}`;
    }

    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isTyping;
    }

    updateCharCounter() {
        const length = this.messageInput.value.length;
        this.charCount.textContent = length;
        
        if (length > 1800) {
            this.charCount.style.color = 'var(--error-color)';
        } else if (length > 1500) {
            this.charCount.style.color = 'var(--warning-color)';
        } else {
            this.charCount.style.color = 'var(--text-muted)';
        }
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        // Hide welcome message on first interaction
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }

        // Add user message
        this.addMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        this.updateSendButton();
        this.updateCharCounter();
        this.autoResizeTextarea();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            await this.getAgentResponse(message);
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('Sorry, I encountered an error while processing your request. Please try again.', 'assistant', true);
        } finally {
            this.hideTypingIndicator();
        }
    }

    async getAgentResponse(message) {
        try {
            // Start diagram animation
            a2aResetAll();
            a2aSetStatus('a2a-user', 'active');
            a2aAddFlow('📝 User: "' + message.substring(0, 60) + (message.length > 60 ? '...' : '') + '"', 'user');

            const response = await fetch((window.BASE_PATH || '') + '/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, session_id: this.sessionId })
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalResponse = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // keep incomplete line

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const payload = line.substring(6).trim();
                    if (payload === '[DONE]') continue;

                    try {
                        const data = JSON.parse(payload);
                        if (data.type === 'trace') {
                            // Live trace event — update diagram and flow
                            var nodeId = 'a2a-' + data.agent;
                            a2aSetStatus(nodeId, data.status);
                            a2aAddFlow(data.msg, data.status);
                        } else if (data.type === 'response') {
                            finalResponse = data;
                        }
                    } catch (e) { /* skip unparseable */ }
                }
            }

            // Show the final response
            if (finalResponse) {
                this.addMessage(finalResponse.response, 'assistant');
                if (finalResponse.session_id) this.sessionId = finalResponse.session_id;
            }
            
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    addMessage(content, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = content;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(timeDiv);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        if (isError) {
            contentDiv.style.background = 'var(--error-color)';
            contentDiv.style.color = 'white';
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store in history
        this.messageHistory.push({ sender, content, timestamp: new Date() });
    }

    showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.style.display = 'flex';
        this.updateSendButton();
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.style.display = 'none';
        this.updateSendButton();
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    clearSession() {
        this.messageHistory = [];
        this.messagesContainer.innerHTML = '';
        this.sessionId = this.generateSessionId();
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'block';
        }
    }
}

// Global functions for example buttons
function sendExample(button) {
    const message = button.textContent.replace(/"/g, '');
    const chat = window.productChat;
    if (chat) {
        chat.messageInput.value = message;
        chat.sendMessage();
    }
}

// (initialization moved to end of file)

// ---- A2A Agent Diagram Logic ----
// Map connection pairs to their SVG line element IDs
var a2aLineMap = {
    'a2a-user|a2a-client': 'user-client',
    'a2a-client|a2a-server': 'client-server',
    'a2a-server|a2a-manager': 'server-manager',
    'a2a-manager|a2a-product': 'manager-product',
    'a2a-manager|a2a-marketing': 'manager-marketing',
    'a2a-manager|a2a-ranker': 'manager-ranker',
};
var a2aConnections = Object.keys(a2aLineMap).map(function(k) { return k.split('|'); });

function a2aDrawLines() {
    // Update main lines + glow lines based on node states
    a2aConnections.forEach(function(pair) {
        var key = a2aLineMap[pair[0] + '|' + pair[1]];
        var line = document.getElementById('line-' + key);
        var glow = document.getElementById('glow-' + key);
        if (!line) return;
        var a = document.getElementById(pair[0]);
        var b = document.getElementById(pair[1]);
        if (!a || !b) return;
        var aOn = a.classList.contains('active') || a.classList.contains('done');
        var bOn = b.classList.contains('active') || b.classList.contains('done');
        var isActive = aOn && bOn;
        if (isActive) {
            // Solid bright line, no dashes
            line.setAttribute('stroke', '#22d3ee');
            line.setAttribute('stroke-width', '2.5');
            line.setAttribute('stroke-opacity', '1');
            line.removeAttribute('stroke-dasharray');
            line.setAttribute('stroke-linecap', 'round');
            // Show glow behind
            if (glow) {
                glow.setAttribute('stroke-opacity', '0.3');
            }
        } else {
            // Faint dashed line
            line.setAttribute('stroke', '#818cf8');
            line.setAttribute('stroke-width', '1.5');
            line.setAttribute('stroke-opacity', '0.45');
            line.setAttribute('stroke-dasharray', '6 4');
            line.removeAttribute('stroke-linecap');
            // Hide glow
            if (glow) {
                glow.setAttribute('stroke-opacity', '0');
            }
        }
    });
}

function a2aSetStatus(nodeId, status) {
    var node = document.getElementById(nodeId);
    console.log('[A2A] setStatus:', nodeId, status, 'found:', !!node);
    if (!node) return;
    node.classList.remove('active', 'done');
    if (status === 'active') node.classList.add('active');
    else if (status === 'done') node.classList.add('done');
    // Log all node states
    var states = {};
    document.querySelectorAll('.a2a-node').forEach(function(n) {
        if (n.classList.contains('active')) states[n.id] = 'active';
        else if (n.classList.contains('done')) states[n.id] = 'done';
    });
    console.log('[A2A] Node states:', JSON.stringify(states));
    a2aDrawLines();
}

function a2aResetAll() {
    document.querySelectorAll('.a2a-node').forEach(function(n) { n.classList.remove('active', 'done'); });
    a2aDrawLines();
}

function a2aAddFlow(text, type) {
    var log = document.getElementById('a2a-flow');
    if (!log) return;
    var entry = document.createElement('div');
    var colors = { active: '#22d3ee', done: '#10b981', user: '#6366f1', info: '#6b7280' };
    var bgs = { active: '#0e2a3a', done: '#0a2e1f', user: '#1e1b4b', info: '#1f2937' };
    entry.style.cssText = 'padding:3px 6px;margin-bottom:3px;border-radius:4px;border-left:3px solid ' + (colors[type]||'#6b7280') + ';background:' + (bgs[type]||'#1f2937');
    var time = new Date().toLocaleTimeString();
    entry.innerHTML = '<span style="color:#6b7280;font-size:0.6rem;">' + time + '</span> ' + text;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function a2aAnimateTrace(trace) {
    // Play trace entries with a small delay between each for visual effect
    var delay = 0;
    trace.forEach(function(t, i) {
        setTimeout(function() {
            var nodeId = 'a2a-' + t.agent;
            a2aSetStatus(nodeId, t.status);
            a2aAddFlow(t.msg, t.status);
        }, delay);
        delay += (t.status === 'active' ? 200 : 100);
    });
}

// Test connectivity on load
fetch((window.BASE_PATH || '') + '/health')
    .then(response => response.json())
    .then(data => {
        console.log('Health check:', data);
        if (window.productChat) window.productChat.updateStatus('connected');
    })
    .catch(error => {
        console.error('Health check failed:', error);
        if (window.productChat) window.productChat.updateStatus('error');
    });

// Handle visibility change to pause/resume when tab is not active
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Page is hidden, can pause timers or reduce activity
    } else {
        // Page is visible, can resume full functionality
        if (window.productChat) {
            window.productChat.scrollToBottom();
        }
    }
});

// Handle browser resize
window.addEventListener('resize', () => {
    if (window.productChat) {
        window.productChat.scrollToBottom();
    }
});

// ---- Initialize everything (must be last so all functions are defined) ----
try {
    window.productChat = new ProductManagementAgentChat();
    setTimeout(a2aDrawLines, 800);
    setTimeout(a2aDrawLines, 1500);  // redraw again after layout settles
    window.addEventListener('resize', a2aDrawLines);
} catch(e) {
    console.error('Failed to initialize chat:', e);
}
