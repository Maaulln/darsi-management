const API = window.location.origin;

const tabs = document.querySelectorAll('.tab');
const navItems = document.querySelectorAll('.nav-item');

navItems.forEach((btn) => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        navItems.forEach((b) => b.classList.toggle('active', b === btn));
        tabs.forEach((tab) => tab.classList.toggle('active', tab.id === `tab-${target}`));
        if (target === 'dashboard') loadOverview();
        if (target === 'analytics') loadAnalytics();
        if (target === 'data') ensureDomains();
    });
});

const numberFormatter = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 });
const idrFormatter = new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
});

function fmt(value) {
    if (value === null || value === undefined || Number.isNaN(value)) return '–';
    return numberFormatter.format(value);
}

function fmtIDR(value) {
    if (!value) return 'Rp 0';
    return idrFormatter.format(value);
}

async function fetchJSON(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`${path} ${response.status}`);
    }
    return response.json();
}

const charts = {};

function renderChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (charts[canvasId]) charts[canvasId].destroy();
    charts[canvasId] = new Chart(ctx, config);
}

async function loadStatus() {
    const pill = document.getElementById('status-pill');
    try {
        const data = await fetchJSON('/api/readiness');
        pill.textContent = `Status: ${data.overall.toUpperCase()}`;
        pill.classList.remove('degraded', 'down');
        if (data.overall !== 'ok') pill.classList.add('degraded');
    } catch (error) {
        pill.textContent = 'Backend tidak terjangkau';
        pill.classList.add('down');
    }
}

async function loadOverview() {
    try {
        const data = await fetchJSON('/api/analytics/overview');
        const k = data.kpi || {};
        document.getElementById('kpi-pasien').textContent = fmt(k.pasien_aktif);
        document.getElementById('kpi-bor').textContent = `${k.bor_pct ?? 0}%`;
        document.getElementById('kpi-bed-detail').textContent = `${fmt(k.bed_occupied)} / ${fmt(k.bed_capacity)} bed`;
        document.getElementById('kpi-kwh').textContent = fmt(k.kwh_total);
        document.getElementById('kpi-air').textContent = fmt(k.air_m3_total);
        document.getElementById('kpi-cost').textContent = fmtIDR(k.total_cost_idr);
        document.getElementById('kpi-budget').textContent = `Budget ${fmtIDR(k.total_budget_idr)} · ${k.budget_usage_pct ?? 0}%`;
        document.getElementById('kpi-overtime-hour').textContent = `${fmt(k.overtime_hours)} jam`;
        document.getElementById('kpi-overtime-cost').textContent = fmtIDR(k.overtime_cost_idr);
    } catch (error) {
        console.warn('overview gagal', error);
    }

    try {
        const occ = await fetchJSON('/api/analytics/occupancy-by-unit');
        const units = occ.units || [];
        renderChart('chart-occupancy', {
            type: 'bar',
            data: {
                labels: units.map((u) => u.unit_code || '?'),
                datasets: [
                    {
                        label: 'Kapasitas',
                        data: units.map((u) => u.capacity || 0),
                        backgroundColor: 'rgba(34, 211, 238, 0.5)',
                    },
                    {
                        label: 'Terisi',
                        data: units.map((u) => u.occupied || 0),
                        backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#cbd5e1' } } },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                },
            },
        });
    } catch (error) {
        console.warn('occupancy gagal', error);
    }

    try {
        const cost = await fetchJSON('/api/analytics/cost-by-category');
        const cats = cost.categories || [];
        renderChart('chart-cost', {
            type: 'doughnut',
            data: {
                labels: cats.map((c) => c.cost_category || 'lain'),
                datasets: [
                    {
                        data: cats.map((c) => c.total_cost || 0),
                        backgroundColor: ['#6366f1', '#22d3ee', '#f59e0b', '#10b981', '#ef4444', '#a855f7', '#3b82f6'],
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#cbd5e1' } } },
            },
        });
    } catch (error) {
        console.warn('cost gagal', error);
    }
}

async function loadAnalytics() {
    try {
        const trend = await fetchJSON('/api/analytics/utility-trend');
        const listrik = trend.listrik || [];
        const air = trend.air || [];
        renderChart('chart-listrik', {
            type: 'bar',
            data: {
                labels: listrik.map((u) => u.unit_code || '?'),
                datasets: [{
                    label: 'kWh',
                    data: listrik.map((u) => u.kwh || 0),
                    backgroundColor: 'rgba(245, 158, 11, 0.65)',
                }],
            },
            options: chartTheme(),
        });
        renderChart('chart-air', {
            type: 'bar',
            data: {
                labels: air.map((u) => u.unit_code || '?'),
                datasets: [{
                    label: 'm³',
                    data: air.map((u) => u.volume || 0),
                    backgroundColor: 'rgba(34, 211, 238, 0.65)',
                }],
            },
            options: chartTheme(),
        });
    } catch (error) {
        console.warn('utility trend gagal', error);
    }

    try {
        const cost = await fetchJSON('/api/analytics/cost-by-category');
        const cats = cost.categories || [];
        renderChart('chart-budget', {
            type: 'bar',
            data: {
                labels: cats.map((c) => c.cost_category || 'lain'),
                datasets: [
                    {
                        label: 'Actual',
                        data: cats.map((c) => c.total_cost || 0),
                        backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    },
                    {
                        label: 'Budget',
                        data: cats.map((c) => c.total_budget || 0),
                        backgroundColor: 'rgba(16, 185, 129, 0.6)',
                    },
                ],
            },
            options: chartTheme(),
        });
    } catch (error) {
        console.warn('budget gagal', error);
    }
}

function chartTheme() {
    return {
        responsive: true,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        },
    };
}

// ────────────────────────────────────────────────────────────────────────────
// Chat tab
// ────────────────────────────────────────────────────────────────────────────

const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const ragToggle = document.getElementById('rag-toggle');
const contextPre = document.getElementById('context-pre');

function appendMessage(text, isUser) {
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    div.textContent = text;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    appendMessage(text, true);
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;
    sendBtn.textContent = '…';
    try {
        const data = await fetchJSON('/api/chat', {
            method: 'POST',
            body: JSON.stringify({ message: text, use_rag: ragToggle.checked }),
        });
        appendMessage(data.response, false);
        contextPre.textContent = (data.context_used || '(no context)').trim();
    } catch (error) {
        appendMessage(`Error: ${error.message}`, false);
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        sendBtn.textContent = 'Kirim';
        userInput.focus();
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') sendMessage();
});

// ────────────────────────────────────────────────────────────────────────────
// Data Explorer tab
// ────────────────────────────────────────────────────────────────────────────

let domainsLoaded = false;

async function ensureDomains() {
    if (domainsLoaded) return;
    try {
        const data = await fetchJSON('/api/data/domains');
        const list = document.getElementById('domain-list');
        list.innerHTML = '';
        (data.domains || []).forEach((domain) => {
            const li = document.createElement('li');
            const btn = document.createElement('button');
            btn.textContent = domain.name;
            btn.addEventListener('click', () => loadDomainRecords(domain.name, btn));
            li.appendChild(btn);
            list.appendChild(li);
        });
        domainsLoaded = true;
    } catch (error) {
        console.warn('domains gagal', error);
    }
}

async function loadDomainRecords(domain, btn) {
    document.querySelectorAll('.domain-list button').forEach((b) => b.classList.toggle('active', b === btn));
    document.getElementById('data-title').textContent = `Domain: ${domain}`;
    document.getElementById('data-meta').textContent = 'Memuat…';
    try {
        const data = await fetchJSON(`/api/data/domain/${domain}?limit=100`);
        const records = data.records || [];
        document.getElementById('data-meta').textContent = `${records.length} record dari ${data.table}`;
        const table = document.getElementById('data-table');
        table.innerHTML = '';
        if (!records.length) {
            table.innerHTML = '<tbody><tr><td>Tidak ada data.</td></tr></tbody>';
            return;
        }
        const columns = Object.keys(records[0]);
        const thead = document.createElement('thead');
        thead.innerHTML = `<tr>${columns.map((c) => `<th>${c}</th>`).join('')}</tr>`;
        table.appendChild(thead);
        const tbody = document.createElement('tbody');
        records.forEach((row) => {
            const tr = document.createElement('tr');
            tr.innerHTML = columns
                .map((c) => `<td>${row[c] === null || row[c] === undefined ? '' : row[c]}</td>`)
                .join('');
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
    } catch (error) {
        document.getElementById('data-meta').textContent = `Gagal: ${error.message}`;
    }
}

// init
document.getElementById('refresh-overview').addEventListener('click', loadOverview);
loadStatus();
loadOverview();
setInterval(loadStatus, 30000);
