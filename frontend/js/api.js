/**
 * api.js — HTTP client for the HC Lead Agent backend API.
 */
const API = (() => {
    const BASE = '';   // same-origin (FastAPI serves both)

    async function _post(path, body = {}) {
        const res = await fetch(BASE + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
    }

    async function _get(path) {
        const res = await fetch(BASE + path);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    return {
        /** Create a new session. Returns { session_id } */
        initSession() {
            return _post('/api/session/init');
        },

        /**
         * Send a chat message.
         * Returns { response, intent, lead_status, quick_replies }
         */
        sendMessage(sessionId, message) {
            return _post('/api/chat', { session_id: sessionId, message });
        },

        /** Health check — returns { status, kb_document_count, kb_ready } */
        health() {
            return _get('/api/health');
        },

        /** Trigger a website re-scrape (admin). */
        triggerScrape() {
            return _post('/api/admin/scrape');
        },
    };
})();
