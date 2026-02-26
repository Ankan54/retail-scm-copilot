/**
 * API service for SupplyChain Copilot Dashboard
 *
 * Local dev: Vite proxies /api/* → http://localhost:8000 (FastAPI + PostgreSQL)
 * Production: set VITE_API_BASE to the API Gateway URL
 */

const API_BASE = 'https://jn5xaobcs6.execute-api.us-east-1.amazonaws.com/prod';

export const T = {
    sidebar: "#1a1f37",
    sidebarHov: "#252a42",
    sidebarAct: "#2f3556",
    sidebarTxt: "#8b8fad",
    bg: "#f0f1f6",
    cardBg: "#ffffff",
    cardBorder: "#e8e9f0",
    cardShadow: "0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)",
    heading: "#1a1f37",
    text: "#3d4260",
    textMuted: "#8b8fad",
    textLight: "#a9adc4",
    primary: "#6366f1",
    primarySoft: "#ededfe",
    teal: "#0ea5e9",
    tealSoft: "#e6f6fe",
    pink: "#ec4899",
    pinkSoft: "#fdf0f7",
    green: "#22c55e",
    greenSoft: "#edfcf2",
    orange: "#f59e0b",
    orangeSoft: "#fef8e7",
    red: "#ef4444",
    redSoft: "#fef2f2",
    purple: "#7c3aed",
    purpleSoft: "#f3f0ff",
};

export const fmt = (n) => {
    if (n == null) return "—";
    if (n >= 10000000) return "₹" + (n / 10000000).toFixed(1) + "Cr";
    if (n >= 100000) return "₹" + (n / 100000).toFixed(1) + "L";
    if (n >= 1000) return "₹" + (n / 1000).toFixed(1) + "K";
    return "₹" + Math.round(n);
};

export const CATEGORY_LABELS = { A: "Platinum", B: "Gold", C: "Silver" };

async function apiFetch(path, params = {}) {
    const qs = Object.keys(params).length ? '?' + new URLSearchParams(params) : '';
    try {
        const res = await fetch(`${API_BASE}${path}${qs}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`API fetch failed: ${path}`, err);
        return null;
    }
}

export const fetchMetrics          = (month) => apiFetch('/api/metrics',           month ? { month } : {});
export const fetchDealers          = ()       => apiFetch('/api/dealers');
export const fetchRevenueChart     = ()       => apiFetch('/api/revenue-chart');
export const fetchCommitmentPipeline = (month) => apiFetch('/api/commitment-pipeline', month ? { month } : {});
export const fetchSalesTeam        = (month) => apiFetch('/api/sales-team',        month ? { month } : {});
export const fetchRecentActivity   = (month) => apiFetch('/api/recent-activity',   month ? { month } : {});
export const fetchWeeklyPipeline   = (month) => apiFetch('/api/weekly-pipeline',   month ? { month } : {});

export async function sendChatMessage(message, sessionId) {
    // Chat goes directly to the Bedrock supervisor agent via /api/chat
    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        return { text: `Error: ${err.message}`, agent: "System" };
    }
}
