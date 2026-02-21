/**
 * chat.js — Main chat application logic.
 * Handles session management, message rendering, typing indicator,
 * quick replies, lead progress bar, and auto-resize input.
 */
(() => {
    // ── State ──────────────────────────────────────────────────────────────────
    let sessionId = null;
    let isWaiting = false;

    // ── DOM refs ───────────────────────────────────────────────────────────────
    const $overlay = document.getElementById('loadingOverlay');
    const $area = document.getElementById('messagesArea');
    const $input = document.getElementById('msgInput');
    const $sendBtn = document.getElementById('sendBtn');
    const $clearBtn = document.getElementById('clearBtn');
    const $qr = document.getElementById('quickReplies');
    const $progress = document.getElementById('leadProgress');
    const $progBar = document.getElementById('progressBar');
    const $progLabel = document.getElementById('progressLabel');
    const $kbText = document.getElementById('kbStatusText');

    // ── Init ───────────────────────────────────────────────────────────────────
    async function init() {
        try {
            const { session_id } = await API.initSession();
            sessionId = session_id;

            // Health check → update KB status
            try {
                const h = await API.health();
                if (h.kb_ready) {
                    $kbText.textContent = `${h.kb_document_count} knowledge chunks ready`;
                } else {
                    $kbText.textContent = 'Building knowledge base… (first run)';
                }
            } catch (_) {
                $kbText.textContent = 'Knowledge base status unknown';
            }

            hideOverlay();
            $input.focus();
        } catch (err) {
            $kbText.textContent = 'Error connecting to server';
            console.error('Init error:', err);
            hideOverlay();
        }
    }

    function hideOverlay() {
        $overlay.classList.add('hidden');
        setTimeout(() => { $overlay.style.display = 'none'; }, 500);
    }

    // ── Message rendering ──────────────────────────────────────────────────────
    function getTimestamp() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    /** Convert basic markdown-like formatting to HTML. */
    function formatText(text) {
        return text
            // Headers (##)
            .replace(/^### (.+)$/gm, '<strong>$1</strong>')
            .replace(/^## (.+)$/gm, '<strong>$1</strong>')
            // Bold (**text**)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            // Italic (*text*)
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            // Inline code
            .replace(/`(.+?)`/g, '<code>$1</code>')
            // Links [text](url)
            .replace(/\[(.+?)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
            // HR
            .replace(/^---$/gm, '<hr/>')
            // Bullet lists (- item)
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            // Wrap consecutive <li> in <ul>
            .replace(/(<li>.*<\/li>\n?)+/gs, (m) => `<ul>${m}</ul>`)
            // Numbered lists (1. item)
            .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
            // Paragraphs — split by double newline
            .split(/\n{2,}/).map(para => {
                para = para.trim();
                if (!para) return '';
                if (para.startsWith('<ul>') || para.startsWith('<hr') || para.startsWith('<ol>')) return para;
                if (para.startsWith('<li>')) return `<ul>${para}</ul>`;
                return `<p>${para.replace(/\n/g, '<br/>')}</p>`;
            }).join('');
    }

    function appendMessage(role, text) {
        const row = document.createElement('div');
        row.className = `msg-row ${role}`;

        const avDiv = document.createElement('div');
        avDiv.className = `msg-avatar ${role === 'bot' ? 'bot-av' : 'user-av'}`;
        avDiv.innerHTML = role === 'bot'
            ? `<svg width="15" height="15" viewBox="0 0 24 24" fill="none"><rect x="5" y="2" width="14" height="18" rx="3" stroke="#00c9a7" stroke-width="2"/><line x1="9" y1="8" x2="15" y2="8" stroke="#00c9a7" stroke-width="2" stroke-linecap="round"/><line x1="9" y1="12" x2="15" y2="12" stroke="#00c9a7" stroke-width="2" stroke-linecap="round"/></svg>`
            : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" fill="white"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="white" stroke-width="2.2" stroke-linecap="round"/></svg>`;

        const colDiv = document.createElement('div');
        colDiv.className = 'msg-content-col';

        const bubble = document.createElement('div');
        bubble.className = `bubble ${role === 'bot' ? 'bot-bubble' : 'user-bubble'}`;
        bubble.innerHTML = formatText(text);

        const timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = getTimestamp();

        colDiv.appendChild(bubble);
        colDiv.appendChild(timeSpan);
        row.appendChild(avDiv);
        row.appendChild(colDiv);
        $area.appendChild(row);
        scrollToBottom();
        return row;
    }

    function showTyping() {
        const row = document.createElement('div');
        row.className = 'msg-row bot typing-row';
        row.id = 'typingIndicator';
        row.innerHTML = `
      <div class="msg-avatar bot-av">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><rect x="5" y="2" width="14" height="18" rx="3" stroke="#00c9a7" stroke-width="2"/></svg>
      </div>
      <div class="msg-content-col">
        <div class="bubble bot-bubble">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>`;
        $area.appendChild(row);
        scrollToBottom();
    }

    function removeTyping() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    function scrollToBottom() {
        $area.scrollTop = $area.scrollHeight;
    }

    // ── Quick Replies ──────────────────────────────────────────────────────────
    function showQuickReplies(replies) {
        $qr.innerHTML = '';
        if (!replies || replies.length === 0) {
            $qr.style.display = 'none';
            return;
        }
        replies.forEach(text => {
            const btn = document.createElement('button');
            btn.className = 'quick-btn';
            btn.textContent = text;
            btn.addEventListener('click', () => {
                hideQuickReplies();
                sendMessage(text);
            });
            $qr.appendChild(btn);
        });
        $qr.style.display = 'flex';
    }

    function hideQuickReplies() {
        $qr.style.display = 'none';
        $qr.innerHTML = '';
    }

    // ── Lead Progress ──────────────────────────────────────────────────────────
    function updateProgress(leadStatus, response) {
        const collectingStates = ['COLLECTING', 'CONFIRMING', 'COMPLETED', 'CONSENT_PENDING'];
        if (!collectingStates.includes(leadStatus)) {
            $progress.style.display = 'none';
            return;
        }

        // Estimate progress from lead_status
        if (leadStatus === 'COMPLETED') {
            setProgress(7, 7);
        } else if (leadStatus === 'CONFIRMING') {
            setProgress(7, 7);
        } else if (leadStatus === 'COLLECTING') {
            // Count confirmed fields by checking response content
            $progress.style.display = 'block';
        } else {
            $progress.style.display = 'block';
            setProgress(0, 7);
        }
    }

    let _collectedCount = 0;
    function setProgress(current, total) {
        _collectedCount = current;
        $progress.style.display = 'block';
        $progBar.style.width = `${Math.round((current / total) * 100)}%`;
        $progLabel.textContent = `${current} / ${total}`;
    }

    function incrementProgress() {
        _collectedCount = Math.min(_collectedCount + 1, 7);
        setProgress(_collectedCount, 7);
    }

    // ── Send a message ─────────────────────────────────────────────────────────
    async function sendMessage(text) {
        text = (text || $input.value).trim();
        if (!text || isWaiting || !sessionId) return;

        hideQuickReplies();
        appendMessage('user', text);
        $input.value = '';
        $input.style.height = 'auto';
        setInputEnabled(false);
        showTyping();

        try {
            const data = await API.sendMessage(sessionId, text);
            removeTyping();
            appendMessage('bot', data.response);

            // Update lead progress
            if (data.lead_status) {
                updateProgress(data.lead_status, data.response);
                if (['COLLECTING', 'CONFIRMING'].includes(data.lead_status)) {
                    incrementProgress();
                }
                if (data.lead_status === 'COMPLETED') {
                    setProgress(7, 7);
                }
            }

            // Show quick replies
            if (data.quick_replies && data.quick_replies.length > 0) {
                showQuickReplies(data.quick_replies);
            }

        } catch (err) {
            removeTyping();
            appendMessage('bot', `⚠️ Sorry, I encountered an error: *${err.message}*. Please try again.`);
            console.error('sendMessage error:', err);
        } finally {
            setInputEnabled(true);
            $input.focus();
        }
    }

    function setInputEnabled(enabled) {
        isWaiting = !enabled;
        $input.disabled = !enabled;
        $sendBtn.disabled = !enabled || $input.value.trim() === '';
    }

    // ── Input auto-resize ──────────────────────────────────────────────────────
    $input.addEventListener('input', () => {
        $input.style.height = 'auto';
        $input.style.height = Math.min($input.scrollHeight, 140) + 'px';
        $sendBtn.disabled = $input.value.trim() === '' || isWaiting;
    });

    $input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    $sendBtn.addEventListener('click', () => sendMessage());

    // ── Clear conversation ─────────────────────────────────────────────────────
    $clearBtn.addEventListener('click', async () => {
        if (!confirm('Clear the conversation and start a new session?')) return;
        $area.innerHTML = '';
        hideQuickReplies();
        $progress.style.display = 'none';
        _collectedCount = 0;
        sessionId = null;
        $overlay.style.display = 'flex';
        $overlay.classList.remove('hidden');
        await init();
    });

    // ── Kick off ───────────────────────────────────────────────────────────────
    init();
})();
